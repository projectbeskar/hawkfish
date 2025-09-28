"""
Fake driver for testing purposes.

This driver provides a mock implementation of the LibvirtDriver interface
for use in unit and integration tests.
"""

from typing import Any


class FakeDriver:
    """Mock libvirt driver for testing."""
    
    def __init__(self) -> None:
        self.attached: list[tuple[str, str]] = []
        self.detached: list[str] = []
        self.systems = {
            "test-vm-001": {
                "Id": "test-vm-001",
                "Name": "test-vm-001",
                "PowerState": "On",
                "ProcessorSummary": {"Count": 2},
                "MemorySummary": {"TotalSystemMemoryGiB": 4},
                "Status": {"State": "Enabled", "Health": "OK"}
            }
        }
    
    def list_systems(self) -> list[dict[str, Any]]:
        """List all systems."""
        return list(self.systems.values())
    
    def get_system(self, system_id: str) -> dict[str, Any] | None:
        """Get system by ID."""
        return self.systems.get(system_id)
    
    def reset_system(self, system_id: str, reset_type: str) -> None:
        """Reset a system."""
        # Mock implementation - just verify system exists
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
    
    def set_boot_override(self, system_id: str, target: str, persist: bool = False) -> None:
        """Set boot override for a system."""
        # Mock implementation - just verify system exists
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
    
    def attach_iso(self, system_id: str, image_path_or_url: str) -> None:
        """Attach ISO to a system."""
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
        self.attached.append((system_id, image_path_or_url))
    
    def detach_iso(self, system_id: str) -> None:
        """Detach ISO from a system."""
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
        self.detached.append(system_id)
    
    def get_manager_info(self) -> dict[str, Any]:
        """Get manager information."""
        return {
            "Id": "manager1",
            "Name": "Test Manager",
            "ManagerType": "BMC",
            "Status": {"State": "Enabled", "Health": "OK"}
        }
    
    def get_chassis_info(self) -> dict[str, Any]:
        """Get chassis information."""
        return {
            "Id": "chassis1", 
            "Name": "Test Chassis",
            "ChassisType": "RackMount",
            "Status": {"State": "Enabled", "Health": "OK"}
        }
    
    def create_snapshot(self, system_id: str, snapshot_name: str) -> None:
        """Create a snapshot."""
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
        # Mock implementation - no-op
    
    def list_libvirt_snapshots(self, system_id: str) -> list[dict[str, Any]]:
        """List snapshots for a system."""
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
        return []
    
    def revert_snapshot(self, system_id: str, snapshot_name: str) -> None:
        """Revert to a snapshot."""
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
        # Mock implementation - no-op
    
    def delete_libvirt_snapshot(self, system_id: str, snapshot_name: str) -> None:
        """Delete a snapshot."""
        if system_id not in self.systems:
            raise ValueError(f"System {system_id} not found")
        # Mock implementation - no-op
    
    def add_system(self, system_id: str, system_data: dict[str, Any]) -> None:
        """Add a system to the fake driver (test helper)."""
        self.systems[system_id] = system_data
    
    def remove_system(self, system_id: str) -> None:
        """Remove a system from the fake driver (test helper)."""
        self.systems.pop(system_id, None)
    
    def clear_operations(self) -> None:
        """Clear operation history (test helper)."""
        self.attached.clear()
        self.detached.clear()
