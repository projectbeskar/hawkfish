import json
import os
from pathlib import Path

import httpx
import typer

app = typer.Typer(add_completion=False, help="HawkFish CLI")


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hawkfish"
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


def load_config() -> dict:
    p = config_path()
    if p.exists():
        data: dict = json.loads(p.read_text())
        return data
    data = {}
    return data


def save_config(cfg: dict) -> None:
    config_path().write_text(json.dumps(cfg))


def api_base() -> str:
    cfg = load_config()
    base: str = cfg.get("url", os.environ.get("HF_API", "http://localhost:8080/redfish/v1"))
    return base


@app.command()
def systems():
    """List systems"""
    url = f"{api_base()}/Systems"
    with httpx.Client() as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
        for m in data.get("Members", []):
            typer.echo(m.get("@odata.id", ""))


@app.command()
def systems_show(system_id: str):
    url = f"{api_base()}/Systems/{system_id}"
    with httpx.Client() as client:
        r = client.get(url)
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def login(url: str = typer.Option("http://localhost:8080/redfish/v1"), username: str = "admin"):
    password = typer.prompt("Password", hide_input=True)
    body = {"UserName": username, "Password": password}
    with httpx.Client() as client:
        r = client.post(f"{url}/SessionService/Sessions", json=body)
        r.raise_for_status()
        tok = r.json().get("X-Auth-Token")
    cfg = load_config()
    cfg["url"] = url
    cfg["token"] = tok
    save_config(cfg)
    typer.echo("Logged in")


@app.command()
def power(system_id: str, on: bool = False, off: bool = False, reset: bool = False):
    """Power operations"""
    if sum([on, off, reset]) != 1:
        typer.echo("Specify exactly one of --on/--off/--reset", err=True)
        raise typer.Exit(code=2)
    if on:
        reset_type = "On"
    elif off:
        reset_type = "ForceOff"
    else:
        reset_type = "ForceRestart"
    url = f"{api_base()}/Systems/{system_id}/Actions/ComputerSystem.Reset"
    with httpx.Client() as client:
        r = client.post(url, json={"ResetType": reset_type})
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo("OK")


@app.command()
def boot(system_id: str, set: str, persist: bool = typer.Option(False, "--persist")):
    target = set.upper()
    enabled = "Continuous" if persist else "Once"
    body = {"Boot": {"BootSourceOverrideTarget": target, "BootSourceOverrideEnabled": enabled}}
    with httpx.Client() as client:
        r = client.patch(f"{api_base()}/Systems/{system_id}", json=body)
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
    typer.echo("Boot updated")


@app.command()
def media_insert(system_id: str, image: str):
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia", json={"SystemId": system_id, "Image": image, "Inserted": True})
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(r.text)


@app.command()
def media_eject(system_id: str):
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia", json={"SystemId": system_id})
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo("Ejected")


@app.command()
def tasks():
    with httpx.Client() as client:
        r = client.get(f"{api_base()}/TaskService/Tasks")
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def task_watch(task_id: str):
    url = f"{api_base()}/TaskService/Tasks/{task_id}"
    with httpx.Client() as client:
        while True:
            r = client.get(url)
            if r.status_code == 404:
                typer.echo("Task not found", err=True)
                raise typer.Exit(code=1)
            data = r.json()
            typer.echo(json.dumps({"state": data.get("TaskState"), "percent": data.get("PercentComplete")}))
            if data.get("TaskState") in {"Completed", "Exception", "Killed"}:
                break
            import time as _t

            _t.sleep(1)


@app.command()
def nodes_create(name: str, vcpus: int = 2, memory: int = 2048, disk: int = 20, image_url: str = ""):
    body = {
        "Name": name,
        "CPU": vcpus,
        "MemoryMiB": memory,
        "DiskGiB": disk,
        "Image": {"url": image_url} if image_url else {},
    }
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Systems", json=body)
        if r.status_code not in (200, 202):
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        loc = r.headers.get("Location")
        if loc:
            typer.echo(f"Task: {loc}")


@app.command()
def nodes_delete(name: str, delete_storage: bool = False):
    with httpx.Client() as client:
        r = client.delete(f"{api_base()}/Systems/{name}", params={"delete_storage": json.dumps(delete_storage)})
        if r.status_code not in (200, 202):
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        loc = r.headers.get("Location")
        if loc:
            typer.echo(f"Task: {loc}")


@app.command()
def events_sse():
    base = api_base().replace('/redfish/v1','')
    with httpx.Client(timeout=300) as client, client.stream("GET", f"{base}/events/stream") as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                print(line)


def main() -> None:
    app()


if __name__ == "__main__":
    main()


