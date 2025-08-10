import os

import httpx
import typer

app = typer.Typer(add_completion=False, help="HawkFish CLI")


def api_base() -> str:
    return os.environ.get("HF_API", "http://localhost:8080/redfish/v1")


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()


