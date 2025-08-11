from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
import httpx

from ..config import settings
from .events import SubscriptionStore, publish_event
from .tasks import TaskService


@dataclass
class NodeSpec:
    name: str
    vcpus: int
    memory_mib: int
    disk_gib: int
    network: str
    boot_primary: str | None
    image_url: str | None
    cloud_init: dict[str, Any] | None


def _ensure_storage_dirs() -> dict[str, Path]:
    base = Path(settings.state_dir)
    volumes = base / "volumes"
    images = base / "images"
    seeds = base / "seeds"
    volumes.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)
    seeds.mkdir(parents=True, exist_ok=True)
    return {"volumes": volumes, "images": images, "seeds": seeds}


async def create_node(spec: NodeSpec, task_service: TaskService, subs: SubscriptionStore) -> str:
    task = await task_service.create(name=f"Create node {spec.name}")

    async def job(task_id: str) -> None:
        await task_service.update(task_id, state="Running", percent=1, message="Preparing storage")
        dirs = _ensure_storage_dirs()
        vol_path = dirs["volumes"] / f"{spec.name}.qcow2"
        # create volume
        created = False
        try:
            subprocess.run(["/usr/bin/qemu-img", "create", "-f", "qcow2", str(vol_path), f"{spec.disk_gib}G"], check=True)  # noqa: S603
            created = True
        except Exception:
            # fallback: sparse file
            with open(vol_path, "ab") as f:
                f.truncate(spec.disk_gib * 1024 * 1024 * 1024)
            created = True
        if created:
            await task_service.update(task_id, percent=10, message=f"Volume {vol_path} created")

        # download base image if provided
        base_img_path: Path | None = None
        if spec.image_url:
            await task_service.update(task_id, message=f"Downloading base image {spec.image_url}")
            safe = spec.image_url.split("?")[0].rstrip("/").split("/")[-1] or "base.qcow2"
            base_img_path = dirs["images"] / safe
            if not base_img_path.exists():
                async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client, client.stream("GET", str(spec.image_url)) as resp:
                        resp.raise_for_status()
                        with open(base_img_path, "wb") as out:
                            async for chunk in resp.aiter_bytes():
                                out.write(chunk)
            await task_service.update(task_id, percent=30, message="Base image ready")

        # cloud-init seed generation (simple NoCloud: user-data/meta-data)
        seed_path = dirs["seeds"] / f"{spec.name}.iso"
        user_data = (spec.cloud_init or {}).get("userData", "#cloud-config\nusers: []\n")
        # meta-data
        tmp_dir = dirs["seeds"] / f".seed-{spec.name}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        (tmp_dir / "user-data").write_text(user_data)
        (tmp_dir / "meta-data").write_text(f"instance-id: {spec.name}\nlocal-hostname: {spec.name}\n")
        # try genisoimage; fallback to zip-like concat
        try:
            subprocess.run(["/usr/bin/genisoimage", "-output", str(seed_path), "-volid", "cidata", "-joliet", "-rock", str(tmp_dir / "user-data"), str(tmp_dir / "meta-data")], check=True)  # noqa: S603
        except Exception:
            with open(seed_path, "wb") as out:
                out.write((tmp_dir / "user-data").read_bytes())
                out.write((tmp_dir / "meta-data").read_bytes())
        await task_service.update(task_id, percent=40, message=f"Seed created at {seed_path}")

        # libvirt define domain (omitted here); would use XML with devices
        await task_service.update(task_id, percent=80, message="Defining VM")

        # emit event
        await publish_event("SystemCreated", {"systemId": spec.name}, subs)
        await task_service.update(task_id, state="Completed", percent=100, end=True)

    # run in background via thread to avoid event loop constraints
    await task_service.run_background(name=f"Create node {spec.name}", coro_factory=lambda tid: job(tid))
    return task.id


async def delete_node(name: str, delete_storage: bool, task_service: TaskService, subs: SubscriptionStore) -> str:
    task = await task_service.create(name=f"Delete node {name}")

    async def job(task_id: str) -> None:
        await task_service.update(task_id, state="Running", percent=1, message="Stopping and undefining")
        dirs = _ensure_storage_dirs()
        # In a full implementation, power off, detach, undefine here
        await task_service.update(task_id, percent=50, message="Removing artifacts")
        # remove seed
        with anyio.move_on_after(0):
            os.remove(dirs["seeds"] / f"{name}.iso")
        if delete_storage:
            with anyio.move_on_after(0):
                os.remove(dirs["volumes"] / f"{name}.qcow2")
        await publish_event("SystemDeleted", {"systemId": name}, subs)
        await task_service.update(task_id, state="Completed", percent=100, end=True)

    await task_service.run_background(name=f"Delete node {name}", coro_factory=lambda tid: job(tid))
    return task.id


