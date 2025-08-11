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


def auth_headers() -> dict:
    cfg = load_config()
    token = cfg.get("token")
    return {"X-Auth-Token": token} if token else {}


@app.command()
def systems():
    """List systems"""
    url = f"{api_base()}/Systems"
    with httpx.Client() as client:
        r = client.get(url, headers=auth_headers())
        r.raise_for_status()
        data = r.json()
        for m in data.get("Members", []):
            typer.echo(m.get("@odata.id", ""))


@app.command()
def systems_show(system_id: str):
    url = f"{api_base()}/Systems/{system_id}"
    with httpx.Client() as client:
        r = client.get(url, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def login(url: str = typer.Option("http://localhost:8080/redfish/v1"), username: str = "admin", insecure: bool = typer.Option(False, "--insecure", help="Skip TLS verify")):
    password = typer.prompt("Password", hide_input=True)
    body = {"UserName": username, "Password": password}
    verify = not insecure
    with httpx.Client(verify=verify) as client:
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
        r = client.post(url, json={"ResetType": reset_type}, headers=auth_headers())
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
        r = client.patch(f"{api_base()}/Systems/{system_id}", json=body, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
    typer.echo("Boot updated")


@app.command()
def media_insert(system_id: str, image: str):
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia", json={"SystemId": system_id, "Image": image, "Inserted": True}, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(r.text)


@app.command()
def media_eject(system_id: str):
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia", json={"SystemId": system_id}, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo("Ejected")


@app.command()
def tasks():
    with httpx.Client() as client:
        r = client.get(f"{api_base()}/TaskService/Tasks", headers=auth_headers())
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def task_watch(task_id: str):
    url = f"{api_base()}/TaskService/Tasks/{task_id}"
    with httpx.Client() as client:
        while True:
            r = client.get(url, headers=auth_headers())
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
        r = client.post(f"{api_base()}/Systems", json=body, headers=auth_headers())
        if r.status_code not in (200, 202):
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        loc = r.headers.get("Location")
        if loc:
            typer.echo(f"Task: {loc}")


@app.command()
def nodes_delete(name: str, delete_storage: bool = False):
    with httpx.Client() as client:
        r = client.delete(f"{api_base()}/Systems/{name}", params={"delete_storage": json.dumps(delete_storage)}, headers=auth_headers())
        if r.status_code not in (200, 202):
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        loc = r.headers.get("Location")
        if loc:
            typer.echo(f"Task: {loc}")


@app.command()
def events_sse():
    base = api_base().replace('/redfish/v1','')
    with httpx.Client(timeout=300) as client, client.stream("GET", f"{base}/events/stream", headers=auth_headers()) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                print(line)


# Profiles commands
@app.command()
def profiles():
    with httpx.Client() as client:
        r = client.get(f"{api_base()}/Oem/HawkFish/Profiles", headers=auth_headers())
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def profile_show(profile_id: str):
    with httpx.Client() as client:
        r = client.get(f"{api_base()}/Oem/HawkFish/Profiles/{profile_id}", headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def profile_create(name: str, cpu: int = 2, memory: int = 2048, disk: int = 20, network: str = "default", boot_primary: str = "Hdd", image_url: str = ""):
    body = {
        "Name": name,
        "CPU": cpu,
        "MemoryMiB": memory,
        "DiskGiB": disk,
        "Network": network,
        "Boot": {"Primary": boot_primary},
        "Image": {"url": image_url} if image_url else {},
    }
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Oem/HawkFish/Profiles", json=body, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json()))


@app.command()
def profile_delete(profile_id: str):
    with httpx.Client() as client:
        r = client.delete(f"{api_base()}/Oem/HawkFish/Profiles/{profile_id}", headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo("Deleted")


# Batch provisioning
@app.command()
def batch_create(profile_id: str, count: int, name_prefix: str = "node", start_index: int = 1, zero_pad: int = 2, max_concurrency: int = 3):
    body = {
        "ProfileId": profile_id,
        "Count": count,
        "NamePrefix": name_prefix,
        "StartIndex": start_index,
        "ZeroPad": zero_pad,
        "MaxConcurrency": max_concurrency,
    }
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Oem/HawkFish/Batches", json=body, headers=auth_headers())
        if r.status_code not in (200, 202):
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json()))


# Import/adopt
@app.command()
def import_scan():
    with httpx.Client() as client:
        r = client.get(f"{api_base()}/Oem/HawkFish/Import/Scan", headers=auth_headers())
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def import_adopt(domains: str, dry_run: bool = False):
    # domains: comma-separated names
    body = {"Domains": [{"Name": d} for d in domains.split(",") if d]}
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/Oem/HawkFish/Import/Adopt", params={"dry_run": json.dumps(dry_run)}, json=body, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json(), indent=2))


# Subscriptions
@app.command()
def subs_list():
    with httpx.Client() as client:
        r = client.get(f"{api_base()}/EventService/Subscriptions", headers=auth_headers())
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def subs_create(destination: str, event_types: str = "", system_ids: str = "", secret: str = ""):
    evts = [e for e in event_types.split(",") if e]
    systems = [s for s in system_ids.split(",") if s]
    body = {"Destination": destination, "EventTypes": evts, "SystemIds": systems}
    if secret:
        body["Secret"] = secret
    with httpx.Client() as client:
        r = client.post(f"{api_base()}/EventService/Subscriptions", json=body, headers=auth_headers())
        if r.status_code >= 400:
            typer.echo(f"Error: {r.status_code} {r.text}", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(r.json()))


def main() -> None:
    app()


if __name__ == "__main__":
    main()


