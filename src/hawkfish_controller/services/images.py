from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite
import httpx

from ..config import settings


@dataclass
class Image:
    id: str
    name: str
    version: str
    url: str | None
    sha256: str | None
    size: int
    local_path: str | None
    created_at: str
    last_used_at: str | None
    labels: dict[str, Any]


async def init_images() -> None:
    """Initialize images database table."""
    images_dir = Path(settings.state_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_images (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                url TEXT,
                sha256 TEXT,
                size INTEGER NOT NULL,
                local_path TEXT,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                labels TEXT NOT NULL,
                UNIQUE(name, version)
            )
            """
        )
        await db.commit()


async def add_image(
    name: str,
    version: str,
    url: str | None = None,
    sha256: str | None = None,
    labels: dict[str, Any] | None = None,
) -> Image:
    """Add a new image to the catalog."""
    await init_images()
    image_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Download and verify if URL provided
    local_path = None
    actual_size = 0
    actual_sha256 = None
    
    if url:
        images_dir = Path(settings.state_dir) / "images"
        safe_name = f"{name}-{version}-{image_id[:8]}"
        local_path = str(images_dir / f"{safe_name}.img")
        
        # Download to temp file first
        with tempfile.NamedTemporaryFile(delete=False, dir=images_dir) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            sha256_hasher = hashlib.sha256()
            async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client, client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(8192):
                        f.write(chunk)
                        sha256_hasher.update(chunk)
                        actual_size += len(chunk)
            
            actual_sha256 = sha256_hasher.hexdigest()
            
            # Verify checksum if provided
            if sha256 and actual_sha256 != sha256:
                os.unlink(tmp_path)
                raise ValueError(f"Checksum mismatch: expected {sha256}, got {actual_sha256}")
            
            # Move to final location
            os.rename(tmp_path, local_path)
            
        except Exception:
            # Clean up temp file on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
    
    image = Image(
        id=image_id,
        name=name,
        version=version,
        url=url,
        sha256=actual_sha256 or sha256,
        size=actual_size,
        local_path=local_path,
        created_at=now,
        last_used_at=None,
        labels=labels or {},
    )
    
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO hf_images (id, name, version, url, sha256, size, local_path, created_at, last_used_at, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                image.id,
                image.name,
                image.version,
                image.url,
                image.sha256,
                image.size,
                image.local_path,
                image.created_at,
                image.last_used_at,
                json.dumps(image.labels),
            ),
        )
        await db.commit()
    
    return image


async def list_images() -> list[Image]:
    """List all images in the catalog."""
    await init_images()
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        cur = await db.execute(
            "SELECT id, name, version, url, sha256, size, local_path, created_at, last_used_at, labels FROM hf_images ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        await cur.close()
    
    return [
        Image(
            id=r[0],
            name=r[1],
            version=r[2],
            url=r[3],
            sha256=r[4],
            size=r[5],
            local_path=r[6],
            created_at=r[7],
            last_used_at=r[8],
            labels=json.loads(r[9] or "{}"),
        )
        for r in rows
    ]


async def get_image(image_id: str) -> Image | None:
    """Get a specific image by ID."""
    await init_images()
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        cur = await db.execute(
            "SELECT id, name, version, url, sha256, size, local_path, created_at, last_used_at, labels FROM hf_images WHERE id=?",
            (image_id,),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return Image(
        id=row[0],
        name=row[1],
        version=row[2],
        url=row[3],
        sha256=row[4],
        size=row[5],
        local_path=row[6],
        created_at=row[7],
        last_used_at=row[8],
        labels=json.loads(row[9] or "{}"),
    )


async def get_image_by_name_version(name: str, version: str) -> Image | None:
    """Get an image by name and version."""
    await init_images()
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        cur = await db.execute(
            "SELECT id, name, version, url, sha256, size, local_path, created_at, last_used_at, labels FROM hf_images WHERE name=? AND version=?",
            (name, version),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return Image(
        id=row[0],
        name=row[1],
        version=row[2],
        url=row[3],
        sha256=row[4],
        size=row[5],
        local_path=row[6],
        created_at=row[7],
        last_used_at=row[8],
        labels=json.loads(row[9] or "{}"),
    )


async def delete_image(image_id: str) -> None:
    """Remove an image from the catalog and delete its file."""
    image = await get_image(image_id)
    if not image:
        return
    
    # Delete local file if it exists
    if image.local_path and os.path.exists(image.local_path):
        os.unlink(image.local_path)
    
    await init_images()
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        await db.execute("DELETE FROM hf_images WHERE id=?", (image_id,))
        await db.commit()


async def update_image_last_used(image_id: str) -> None:
    """Update the last_used_at timestamp for an image."""
    await init_images()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    async with aiosqlite.connect(f"{settings.state_dir}/images.db") as db:
        await db.execute(
            "UPDATE hf_images SET last_used_at=? WHERE id=?",
            (now, image_id),
        )
        await db.commit()


async def prune_unused_images() -> list[str]:
    """Remove unreferenced images (safe guard - in real implementation would check references)."""
    await init_images()
    
    # For now, just return empty list as we'd need to implement reference checking
    # In a full implementation, this would:
    # 1. Check which images are referenced by profiles/nodes
    # 2. Remove only unreferenced images
    # 3. Return list of pruned image IDs
    
    return []
