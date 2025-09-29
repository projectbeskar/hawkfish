#!/usr/bin/env python3
"""
Complete system lifecycle management example.

This example demonstrates the full lifecycle of a virtual machine in HawkFish:
- Profile creation and management
- System creation from profiles
- Power management and boot configuration
- Virtual media operations
- System monitoring and updates
- Cleanup and deletion

Prerequisites:
- HawkFish controller running with libvirt support
- Valid authentication credentials
- Available host with sufficient resources

Environment Variables:
    HAWKFISH_URL - Controller URL (default: http://localhost:8080)
    HAWKFISH_USERNAME - Username (default: local)
    HAWKFISH_PASSWORD - Password (default: empty)
    PROJECT_ID - Project ID (optional, uses default project)
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict

import httpx


class SystemLifecycleManager:
    """Manages complete system lifecycle operations."""
    
    def __init__(self, base_url: str, username: str = "local", password: str = ""):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session_token: str | None = None
        self.client = httpx.AsyncClient(verify=False, timeout=60.0)
        self.created_resources = {
            "profiles": [],
            "systems": [],
            "images": []
        }
    
    async def __aenter__(self):
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"\nException occurred: {exc_val}")
            print("Attempting cleanup of created resources...")
            await self.cleanup_resources()
        await self.client.aclose()
    
    async def login(self) -> None:
        """Authenticate and obtain session token."""
        print(f"Authenticating as {self.username}...")
        
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/SessionService/Sessions",
            json={"UserName": self.username, "Password": self.password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.session_token = data["SessionToken"]
        print("✓ Authentication successful")
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["X-Auth-Token"] = self.session_token
        return headers
    
    async def create_profile(self, profile_spec: Dict[str, Any]) -> str:
        """Create a system profile."""
        print(f"Creating profile '{profile_spec['Name']}'...")
        
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Oem/HawkFish/Profiles",
            headers=self._headers(),
            json=profile_spec
        )
        response.raise_for_status()
        
        data = response.json()
        profile_id = data["Id"]
        self.created_resources["profiles"].append(profile_id)
        
        print(f"✓ Profile created: {profile_id}")
        print(f"  CPU: {profile_spec['CPU']} cores")
        print(f"  Memory: {profile_spec['MemoryMiB']} MB")
        print(f"  Disk: {profile_spec['DiskGiB']} GB")
        
        return profile_id
    
    async def create_system(self, name: str, profile_id: str, project_id: str | None = None) -> str:
        """Create a system from a profile."""
        print(f"Creating system '{name}' from profile {profile_id}...")
        
        payload = {
            "Name": name,
            "ProfileId": profile_id
        }
        
        if project_id:
            payload["ProjectId"] = project_id
        
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Systems",
            headers=self._headers(),
            json=payload
        )
        
        if response.status_code == 202:
            # Long-running operation
            location = response.headers.get("Location", "")
            task_id = location.split("/")[-1] if location else None
            
            if task_id:
                print(f"  System creation task: {task_id}")
                system_id = await self.wait_for_task_completion(task_id, "system creation")
            else:
                raise Exception("Task ID not found in response")
        else:
            response.raise_for_status()
            data = response.json()
            system_id = data.get("Id", name)
        
        self.created_resources["systems"].append(system_id)
        print(f"✓ System created: {system_id}")
        
        return system_id
    
    async def wait_for_task_completion(self, task_id: str, operation_name: str) -> str:
        """Wait for a task to complete and return the result."""
        print(f"  Waiting for {operation_name} to complete...")
        
        start_time = time.time()
        timeout = 300  # 5 minutes
        
        while time.time() - start_time < timeout:
            response = await self.client.get(
                f"{self.base_url}/redfish/v1/TaskService/Tasks/{task_id}",
                headers=self._headers()
            )
            response.raise_for_status()
            
            task_data = response.json()
            state = task_data.get("TaskState", "Unknown")
            percent = task_data.get("PercentComplete", 0)
            
            print(f"    Progress: {state} ({percent}%)")
            
            if state == "Completed":
                # Extract result from task
                result = task_data.get("Oem", {}).get("HawkFish", {}).get("Result", {})
                return result.get("Id", "unknown")
            elif state == "Exception":
                error_msg = task_data.get("Messages", [{}])[0].get("Message", "Task failed")
                raise Exception(f"{operation_name} failed: {error_msg}")
            
            await asyncio.sleep(2)
        
        raise Exception(f"{operation_name} timed out after {timeout} seconds")
    
    async def get_system_info(self, system_id: str) -> Dict[str, Any]:
        """Get detailed system information."""
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems/{system_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def power_control(self, system_id: str, reset_type: str) -> bool:
        """Control system power state."""
        print(f"Setting power state to {reset_type}...")
        
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset",
            headers=self._headers(),
            json={"ResetType": reset_type}
        )
        response.raise_for_status()
        
        result = response.json()
        task_state = result.get("TaskState", "Unknown")
        print(f"  ✓ Power action completed: {task_state}")
        
        return task_state == "Completed"
    
    async def wait_for_power_state(self, system_id: str, target_state: str, timeout: int = 60) -> bool:
        """Wait for system to reach target power state."""
        print(f"  Waiting for power state: {target_state}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            system_info = await self.get_system_info(system_id)
            current_state = system_info.get("PowerState", "Unknown")
            
            if current_state == target_state:
                print(f"  ✓ Power state reached: {target_state}")
                return True
            elif current_state in ["PoweringOn", "PoweringOff"]:
                print(f"    Transitioning: {current_state}")
            
            await asyncio.sleep(2)
        
        print(f"  ⚠ Timeout waiting for power state {target_state}")
        return False
    
    async def configure_boot(self, system_id: str, boot_source: str, enabled: str = "Once") -> None:
        """Configure system boot settings."""
        print(f"Configuring boot: {boot_source} ({enabled})")
        
        response = await self.client.patch(
            f"{self.base_url}/redfish/v1/Systems/{system_id}",
            headers=self._headers(),
            json={
                "Boot": {
                    "BootSourceOverrideTarget": boot_source,
                    "BootSourceOverrideEnabled": enabled
                }
            }
        )
        response.raise_for_status()
        print("  ✓ Boot configuration updated")
    
    async def insert_virtual_media(self, system_id: str, image_uri: str, device: str = "Cd") -> None:
        """Insert virtual media into system."""
        print(f"Inserting virtual media: {image_uri}")
        
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Systems/{system_id}/VirtualMedia/{device}/Actions/VirtualMedia.InsertMedia",
            headers=self._headers(),
            json={
                "Image": image_uri,
                "WriteProtected": True
            }
        )
        response.raise_for_status()
        
        result = response.json()
        task_state = result.get("TaskState", "Unknown")
        print(f"  ✓ Media inserted: {task_state}")
    
    async def eject_virtual_media(self, system_id: str, device: str = "Cd") -> None:
        """Eject virtual media from system."""
        print(f"Ejecting virtual media from {device}")
        
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Systems/{system_id}/VirtualMedia/{device}/Actions/VirtualMedia.EjectMedia",
            headers=self._headers()
        )
        response.raise_for_status()
        
        result = response.json()
        task_state = result.get("TaskState", "Unknown")
        print(f"  ✓ Media ejected: {task_state}")
    
    async def monitor_system(self, system_id: str, duration: int = 30) -> None:
        """Monitor system for a specified duration."""
        print(f"Monitoring system for {duration} seconds...")
        
        start_time = time.time()
        last_state = None
        
        while time.time() - start_time < duration:
            try:
                system_info = await self.get_system_info(system_id)
                current_state = system_info.get("PowerState", "Unknown")
                
                if current_state != last_state:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"  [{timestamp}] Power state: {current_state}")
                    last_state = current_state
                
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"  Monitoring error: {e}")
                break
        
        print("  ✓ Monitoring completed")
    
    async def delete_system(self, system_id: str, force: bool = False) -> None:
        """Delete a system."""
        print(f"Deleting system {system_id}...")
        
        # Ensure system is powered off first
        try:
            system_info = await self.get_system_info(system_id)
            if system_info.get("PowerState") == "On":
                await self.power_control(system_id, "ForceOff")
                await self.wait_for_power_state(system_id, "Off", timeout=30)
        except Exception:
            pass  # Continue with deletion even if power off fails
        
        params = {}
        if force:
            params["force"] = "true"
        
        response = await self.client.delete(
            f"{self.base_url}/redfish/v1/Systems/{system_id}",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        
        print(f"  ✓ System deleted: {system_id}")
        
        # Remove from our tracking
        if system_id in self.created_resources["systems"]:
            self.created_resources["systems"].remove(system_id)
    
    async def delete_profile(self, profile_id: str) -> None:
        """Delete a profile."""
        print(f"Deleting profile {profile_id}...")
        
        response = await self.client.delete(
            f"{self.base_url}/redfish/v1/Oem/HawkFish/Profiles/{profile_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        
        print(f"  ✓ Profile deleted: {profile_id}")
        
        # Remove from our tracking
        if profile_id in self.created_resources["profiles"]:
            self.created_resources["profiles"].remove(profile_id)
    
    async def cleanup_resources(self) -> None:
        """Clean up all created resources."""
        print("\nCleaning up created resources...")
        
        # Delete systems first
        for system_id in self.created_resources["systems"].copy():
            try:
                await self.delete_system(system_id, force=True)
            except Exception as e:
                print(f"  ⚠ Failed to delete system {system_id}: {e}")
        
        # Then delete profiles
        for profile_id in self.created_resources["profiles"].copy():
            try:
                await self.delete_profile(profile_id)
            except Exception as e:
                print(f"  ⚠ Failed to delete profile {profile_id}: {e}")
        
        print("✓ Cleanup completed")


async def demo_lifecycle():
    """Demonstrate complete system lifecycle."""
    
    # Configuration
    base_url = os.getenv("HAWKFISH_URL", "http://localhost:8080")
    username = os.getenv("HAWKFISH_USERNAME", "local")
    password = os.getenv("HAWKFISH_PASSWORD", "")
    project_id = os.getenv("PROJECT_ID")
    
    print("HawkFish System Lifecycle Demo")
    print("=" * 40)
    print(f"URL: {base_url}")
    print(f"Username: {username}")
    if project_id:
        print(f"Project: {project_id}")
    print()
    
    async with SystemLifecycleManager(base_url, username, password) as manager:
        
        # Step 1: Create a profile
        print("Step 1: Creating system profile")
        print("-" * 30)
        
        profile_spec = {
            "Name": "demo-profile",
            "Description": "Demo profile for lifecycle example",
            "CPU": 2,
            "MemoryMiB": 2048,
            "DiskGiB": 20,
            "Network": "default",
            "Boot": {
                "Primary": "Hdd"
            }
        }
        
        profile_id = await manager.create_profile(profile_spec)
        print()
        
        # Step 2: Create system from profile
        print("Step 2: Creating system from profile")
        print("-" * 35)
        
        system_name = f"demo-vm-{int(time.time())}"
        system_id = await manager.create_system(system_name, profile_id, project_id)
        print()
        
        # Step 3: Get initial system information
        print("Step 3: Initial system information")
        print("-" * 33)
        
        system_info = await manager.get_system_info(system_id)
        print(f"✓ System Name: {system_info.get('Name', 'Unknown')}")
        print(f"  Power State: {system_info.get('PowerState', 'Unknown')}")
        print(f"  CPU Cores: {system_info.get('ProcessorSummary', {}).get('Count', 'Unknown')}")
        print(f"  Memory: {system_info.get('MemorySummary', {}).get('TotalSystemMemoryGiB', 'Unknown')} GB")
        print()
        
        # Step 4: Configure boot for installation
        print("Step 4: Configuring boot for installation")
        print("-" * 38)
        
        await manager.configure_boot(system_id, "Cd", "Once")
        
        # Insert installation media (if URI provided)
        install_image = os.getenv("INSTALL_IMAGE_URI", "http://example.com/ubuntu-22.04.iso")
        await manager.insert_virtual_media(system_id, install_image)
        print()
        
        # Step 5: Power on system
        print("Step 5: Powering on system for installation")
        print("-" * 40)
        
        await manager.power_control(system_id, "On")
        await manager.wait_for_power_state(system_id, "On")
        print()
        
        # Step 6: Monitor system during "installation"
        print("Step 6: Monitoring system (simulating installation)")
        print("-" * 50)
        
        await manager.monitor_system(system_id, duration=20)
        print()
        
        # Step 7: Complete installation process
        print("Step 7: Completing installation process")
        print("-" * 36)
        
        # Eject installation media
        await manager.eject_virtual_media(system_id)
        
        # Reset boot configuration
        await manager.configure_boot(system_id, "Hdd", "Continuous")
        
        # Restart system to boot from disk
        await manager.power_control(system_id, "ForceRestart")
        await manager.wait_for_power_state(system_id, "On")
        print()
        
        # Step 8: Final system verification
        print("Step 8: Final system verification")
        print("-" * 31)
        
        final_info = await manager.get_system_info(system_id)
        boot_config = final_info.get("Boot", {})
        print("✓ System operational")
        print(f"  Power State: {final_info.get('PowerState', 'Unknown')}")
        print(f"  Boot Source: {boot_config.get('BootSourceOverrideTarget', 'Hdd')}")
        print(f"  Boot Enabled: {boot_config.get('BootSourceOverrideEnabled', 'Disabled')}")
        print()
        
        # Step 9: Lifecycle management demonstration
        print("Step 9: Lifecycle management operations")
        print("-" * 38)
        
        # Demonstrate graceful shutdown
        await manager.power_control(system_id, "GracefulShutdown")
        await manager.wait_for_power_state(system_id, "Off")
        
        # Power back on
        await manager.power_control(system_id, "On")
        await manager.wait_for_power_state(system_id, "On")
        print()
        
        # Step 10: Cleanup (optional - can be skipped for manual testing)
        cleanup = os.getenv("DEMO_CLEANUP", "true").lower() == "true"
        if cleanup:
            print("Step 10: Cleanup resources")
            print("-" * 24)
            
            await manager.delete_system(system_id)
            await manager.delete_profile(profile_id)
            print()
        else:
            print("Step 10: Cleanup skipped (DEMO_CLEANUP=false)")
            print("Resources created:")
            print(f"  System: {system_id}")
            print(f"  Profile: {profile_id}")
            print()
        
        print("✓ System lifecycle demo completed successfully!")
        print("\nThis demo showed:")
        print("  • Profile creation and management")
        print("  • System creation with task monitoring")
        print("  • Power state management")
        print("  • Boot configuration")
        print("  • Virtual media operations")
        print("  • System monitoring")
        print("  • Resource cleanup")


def main():
    """Main entry point."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        return 0
    
    try:
        return asyncio.run(demo_lifecycle())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nDemo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
