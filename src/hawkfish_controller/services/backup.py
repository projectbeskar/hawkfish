from __future__ import annotations

import json
import logging
import os
import sqlite3
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class BackupService:
    """Service for backing up and restoring HawkFish state."""
    
    def __init__(self, state_dir: str | None = None):
        self.state_dir = Path(state_dir or settings.state_dir)
        self.db_path = self.state_dir / "hawkfish.db"
    
    def create_backup(self, output_path: str) -> dict[str, Any]:
        """Create a backup of HawkFish state.
        
        Args:
            output_path: Path where to save the backup archive
            
        Returns:
            Backup metadata
        """
        output_path = Path(output_path)
        backup_time = datetime.utcnow()
        
        logger.info(f"Creating backup to {output_path}")
        
        # Create temporary directory for backup staging
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Backup SQLite database
            db_backup_path = temp_path / "hawkfish.db"
            self._backup_database(str(db_backup_path))
            
            # Backup configuration
            config_backup_path = temp_path / "config.json"
            self._backup_config(config_backup_path)
            
            # Backup profiles/images index (not the large files themselves)
            index_backup_path = temp_path / "index.json"
            self._backup_index(index_backup_path)
            
            # Create backup metadata
            metadata = {
                "version": "0.7.0",
                "created_at": backup_time.isoformat(),
                "hawkfish_version": "0.7.0",
                "backup_type": "full",
                "components": ["database", "config", "index"]
            }
            
            metadata_path = temp_path / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Create compressed archive
            with tarfile.open(output_path, "w:gz") as tar:
                for file_path in temp_path.iterdir():
                    tar.add(file_path, arcname=file_path.name)
            
        logger.info(f"Backup created successfully: {output_path}")
        return {
            "backup_path": str(output_path),
            "size_bytes": output_path.stat().st_size,
            "created_at": backup_time.isoformat(),
            "components": metadata["components"]
        }
    
    def restore_backup(self, backup_path: str, force: bool = False) -> dict[str, Any]:
        """Restore HawkFish state from backup.
        
        Args:
            backup_path: Path to backup archive
            force: Skip safety checks
            
        Returns:
            Restore metadata
        """
        backup_path = Path(backup_path)
        restore_time = datetime.utcnow()
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        logger.info(f"Restoring backup from {backup_path}")
        
        # Safety check: ensure state directory exists
        if not force and self.db_path.exists():
            raise ValueError(
                "Database already exists. Use force=True to overwrite or backup current state first."
            )
        
        # Create temporary directory for restore staging
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract backup archive
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_path)
            
            # Read backup metadata
            metadata_path = temp_path / "metadata.json"
            if not metadata_path.exists():
                raise ValueError("Invalid backup: missing metadata.json")
            
            with open(metadata_path) as f:
                metadata = json.load(f)
            
            # Version compatibility check
            backup_version = metadata.get("hawkfish_version", "0.0.0")
            if not self._is_compatible_version(backup_version):
                if not force:
                    raise ValueError(
                        f"Backup version {backup_version} may not be compatible with current version 0.7.0. "
                        "Use force=True to attempt restore anyway."
                    )
            
            # Ensure state directory exists
            self.state_dir.mkdir(parents=True, exist_ok=True)
            
            # Restore database
            db_backup_path = temp_path / "hawkfish.db"
            if db_backup_path.exists():
                self._restore_database(str(db_backup_path))
                logger.info("Database restored")
            
            # Restore configuration
            config_backup_path = temp_path / "config.json"
            if config_backup_path.exists():
                self._restore_config(config_backup_path)
                logger.info("Configuration restored")
            
            # Note: Index restore would involve recreating image/profile references
            # but not downloading large files
        
        logger.info(f"Backup restored successfully from {backup_path}")
        return {
            "backup_path": str(backup_path),
            "restored_at": restore_time.isoformat(),
            "backup_version": metadata.get("hawkfish_version"),
            "components_restored": metadata.get("components", [])
        }
    
    def _backup_database(self, output_path: str) -> None:
        """Backup SQLite database using built-in backup API."""
        if not self.db_path.exists():
            logger.warning("Database does not exist, skipping backup")
            return
        
        # Use SQLite backup API for atomic backup
        source_conn = sqlite3.connect(str(self.db_path))
        backup_conn = sqlite3.connect(output_path)
        
        try:
            source_conn.backup(backup_conn)
            logger.debug(f"Database backed up to {output_path}")
        finally:
            source_conn.close()
            backup_conn.close()
    
    def _restore_database(self, backup_path: str) -> None:
        """Restore SQLite database."""
        if self.db_path.exists():
            # Move existing database to backup
            backup_existing = self.db_path.with_suffix(".db.bak")
            self.db_path.rename(backup_existing)
            logger.info(f"Existing database backed up to {backup_existing}")
        
        # Copy backup to destination
        backup_conn = sqlite3.connect(backup_path)
        restore_conn = sqlite3.connect(str(self.db_path))
        
        try:
            backup_conn.backup(restore_conn)
            logger.debug(f"Database restored from {backup_path}")
        finally:
            backup_conn.close()
            restore_conn.close()
    
    def _backup_config(self, output_path: Path) -> None:
        """Backup current configuration."""
        config_data = {
            "state_dir": str(self.state_dir),
            "iso_dir": settings.iso_dir,
            "api_host": settings.api_host,
            "api_port": settings.api_port,
            "auth_mode": settings.auth_mode,
            "ui_enabled": settings.ui_enabled,
            "libvirt_uri": settings.libvirt_uri,
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(output_path, "w") as f:
            json.dump(config_data, f, indent=2)
    
    def _restore_config(self, backup_path: Path) -> None:
        """Restore configuration (currently just logs the values)."""
        with open(backup_path) as f:
            config_data = json.load(f)
        
        logger.info("Configuration from backup:")
        for key, value in config_data.items():
            if key != "created_at":
                logger.info(f"  {key}: {value}")
    
    def _backup_index(self, output_path: Path) -> None:
        """Backup index of profiles and images (metadata only)."""
        index_data = {
            "created_at": datetime.utcnow().isoformat(),
            "note": "This backup contains metadata only. Large files (ISOs, images) are not included.",
            "profiles_count": 0,
            "images_count": 0,
            "state_dir": str(self.state_dir)
        }
        
        # In a real implementation, we'd query the database for counts
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Count profiles
                cursor.execute("SELECT COUNT(*) FROM hf_profiles")
                index_data["profiles_count"] = cursor.fetchone()[0]
                
                # Count images  
                cursor.execute("SELECT COUNT(*) FROM hf_images")
                index_data["images_count"] = cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logger.warning(f"Could not read database for index: {e}")
        
        with open(output_path, "w") as f:
            json.dump(index_data, f, indent=2)
    
    def _is_compatible_version(self, backup_version: str) -> bool:
        """Check if backup version is compatible with current version."""
        # Simple version compatibility check
        # In practice, this would be more sophisticated
        current_major = 0
        backup_major = int(backup_version.split('.')[0]) if backup_version else 0
        
        return backup_major == current_major
    
    def list_databases(self) -> list[dict[str, Any]]:
        """List available database files in state directory."""
        databases = []
        
        for db_file in self.state_dir.glob("*.db*"):
            try:
                stat = db_file.stat()
                databases.append({
                    "name": db_file.name,
                    "path": str(db_file),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except OSError:
                continue
        
        return sorted(databases, key=lambda x: x["modified_at"], reverse=True)


# Global backup service instance
backup_service = BackupService()
