#!/usr/bin/env python3
"""
Basic HawkFish API operations example.

This example demonstrates essential API operations including:
- Authentication and session management
- System power control
- Virtual media operations
- Basic system information retrieval

Prerequisites:
- HawkFish controller running
- Valid credentials for authentication

Environment Variables:
    HAWKFISH_URL - Controller URL (default: http://localhost:8080)
    HAWKFISH_USERNAME - Username (default: local)
    HAWKFISH_PASSWORD - Password (default: empty)
    SYSTEM_ID - Target system ID (optional, uses first available system)
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

import httpx


class HawkFishBasicClient:
    """Simple HawkFish client for basic operations."""
    
    def __init__(self, base_url: str, username: str = "local", password: str = ""):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None
        self.client = httpx.AsyncClient(verify=False, timeout=30.0)
    
    async def __aenter__(self):
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self) -> None:
        """Authenticate and obtain session token."""
        print(f"Authenticating as {self.username}...")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/redfish/v1/SessionService/Sessions",
                json={"UserName": self.username, "Password": self.password}
            )
            response.raise_for_status()
            
            data = response.json()
            self.session_token = data["SessionToken"]
            print("✓ Authentication successful")
            
        except httpx.HTTPStatusError as e:
            print(f"✗ Authentication failed: {e.response.status_code}")
            if e.response.status_code == 401:
                print("  Check username and password")
            raise
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            raise
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["X-Auth-Token"] = self.session_token
        return headers
    
    async def get_service_root(self) -> Dict[str, Any]:
        """Get Redfish service root information."""
        print("Getting service root information...")
        
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/",
            headers=self._headers()
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Connected to {data.get('Id', 'HawkFish')} {data.get('Version', 'Unknown')}")
        return data
    
    async def list_systems(self) -> Dict[str, Any]:
        """List all available systems."""
        print("Listing systems...")
        
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems",
            headers=self._headers()
        )
        response.raise_for_status()
        
        data = response.json()
        systems = data.get("Members", [])
        print(f"✓ Found {len(systems)} systems")
        
        for system in systems:
            system_id = system["@odata.id"].split("/")[-1]
            print(f"  - {system_id}")
        
        return data
    
    async def get_system_info(self, system_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific system."""
        print(f"Getting information for system {system_id}...")
        
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems/{system_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ System: {data.get('Name', system_id)}")
        print(f"  Power State: {data.get('PowerState', 'Unknown')}")
        print(f"  CPU: {data.get('ProcessorSummary', {}).get('Count', 'Unknown')} cores")
        print(f"  Memory: {data.get('MemorySummary', {}).get('TotalSystemMemoryGiB', 'Unknown')} GB")
        
        return data
    
    async def power_control(self, system_id: str, reset_type: str) -> bool:
        """Control system power state."""
        print(f"Sending power action '{reset_type}' to system {system_id}...")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset",
                headers=self._headers(),
                json={"ResetType": reset_type}
            )
            response.raise_for_status()
            
            result = response.json()
            task_state = result.get("TaskState", "Unknown")
            print(f"✓ Power action completed: {task_state}")
            return task_state == "Completed"
            
        except httpx.HTTPStatusError as e:
            print(f"✗ Power action failed: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                if "error" in error_detail:
                    message = error_detail["error"].get("message", "Unknown error")
                    print(f"  Error: {message}")
            except:
                pass
            return False
    
    async def get_virtual_media(self, system_id: str) -> Dict[str, Any]:
        """Get virtual media information for a system."""
        print(f"Getting virtual media for system {system_id}...")
        
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems/{system_id}/VirtualMedia",
            headers=self._headers()
        )
        response.raise_for_status()
        
        data = response.json()
        media_devices = data.get("Members", [])
        print(f"✓ Found {len(media_devices)} virtual media devices")
        
        # Get details for each device
        for device in media_devices:
            device_id = device["@odata.id"].split("/")[-1]
            device_response = await self.client.get(
                f"{self.base_url}{device['@odata.id']}",
                headers=self._headers()
            )
            device_data = device_response.json()
            
            inserted = device_data.get("Inserted", False)
            media_types = device_data.get("MediaTypes", [])
            print(f"  - {device_id}: {', '.join(media_types)} (Inserted: {inserted})")
        
        return data
    
    async def insert_media(self, system_id: str, image_uri: str, device: str = "Cd") -> bool:
        """Insert virtual media into a system."""
        print(f"Inserting media {image_uri} into {device} device...")
        
        try:
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
            print(f"✓ Media insertion completed: {task_state}")
            return task_state == "Completed"
            
        except httpx.HTTPStatusError as e:
            print(f"✗ Media insertion failed: {e.response.status_code}")
            return False
    
    async def eject_media(self, system_id: str, device: str = "Cd") -> bool:
        """Eject virtual media from a system."""
        print(f"Ejecting media from {device} device...")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/redfish/v1/Systems/{system_id}/VirtualMedia/{device}/Actions/VirtualMedia.EjectMedia",
                headers=self._headers()
            )
            response.raise_for_status()
            
            result = response.json()
            task_state = result.get("TaskState", "Unknown")
            print(f"✓ Media ejection completed: {task_state}")
            return task_state == "Completed"
            
        except httpx.HTTPStatusError as e:
            print(f"✗ Media ejection failed: {e.response.status_code}")
            return False
    
    async def set_boot_override(self, system_id: str, boot_source: str, enabled: str = "Once") -> bool:
        """Set boot source override."""
        print(f"Setting boot override to {boot_source} ({enabled})...")
        
        try:
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
            
            print(f"✓ Boot override set to {boot_source}")
            return True
            
        except httpx.HTTPStatusError as e:
            print(f"✗ Boot override failed: {e.response.status_code}")
            return False


async def demo_basic_operations():
    """Demonstrate basic HawkFish operations."""
    
    # Configuration
    base_url = os.getenv("HAWKFISH_URL", "http://localhost:8080")
    username = os.getenv("HAWKFISH_USERNAME", "local")
    password = os.getenv("HAWKFISH_PASSWORD", "")
    system_id = os.getenv("SYSTEM_ID")
    
    print("HawkFish Basic Operations Demo")
    print("=" * 40)
    print(f"URL: {base_url}")
    print(f"Username: {username}")
    print()
    
    try:
        async with HawkFishBasicClient(base_url, username, password) as client:
            
            # 1. Get service information
            await client.get_service_root()
            print()
            
            # 2. List systems
            systems_data = await client.list_systems()
            systems = systems_data.get("Members", [])
            print()
            
            if not systems:
                print("No systems available. Create a system first:")
                print("  hawkfish systems-create test-vm --profile small")
                return
            
            # Use specified system or first available
            if not system_id:
                system_id = systems[0]["@odata.id"].split("/")[-1]
                print(f"Using first available system: {system_id}")
                print()
            
            # 3. Get system details
            await client.get_system_info(system_id)
            print()
            
            # 4. Check virtual media
            await client.get_virtual_media(system_id)
            print()
            
            # 5. Demonstrate power control
            print("Demonstrating power control...")
            current_info = await client.get_system_info(system_id)
            current_power = current_info.get("PowerState", "Unknown")
            
            if current_power == "Off":
                await client.power_control(system_id, "On")
            elif current_power == "On":
                print("System is already on, demonstrating graceful shutdown...")
                await client.power_control(system_id, "GracefulShutdown")
            else:
                print(f"System power state is {current_power}, skipping power demo")
            print()
            
            # 6. Demonstrate boot configuration
            print("Demonstrating boot configuration...")
            await client.set_boot_override(system_id, "Cd", "Once")
            print()
            
            # 7. Demonstrate virtual media (if image URI provided)
            test_image = os.getenv("TEST_IMAGE_URI")
            if test_image:
                print("Demonstrating virtual media operations...")
                await client.insert_media(system_id, test_image)
                await asyncio.sleep(2)  # Brief pause
                await client.eject_media(system_id)
            else:
                print("Virtual media demo skipped (set TEST_IMAGE_URI to enable)")
            print()
            
            print("✓ Basic operations demo completed successfully!")
            
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


async def interactive_mode():
    """Interactive mode for exploring HawkFish API."""
    
    base_url = os.getenv("HAWKFISH_URL", "http://localhost:8080")
    username = os.getenv("HAWKFISH_USERNAME", "local") 
    password = os.getenv("HAWKFISH_PASSWORD", "")
    
    print("HawkFish Interactive Mode")
    print("=" * 30)
    
    async with HawkFishBasicClient(base_url, username, password) as client:
        
        # Get available systems
        systems_data = await client.list_systems()
        systems = systems_data.get("Members", [])
        
        if not systems:
            print("No systems available for interactive mode")
            return
        
        system_ids = [s["@odata.id"].split("/")[-1] for s in systems]
        
        while True:
            print("\nAvailable operations:")
            print("  1. List systems")
            print("  2. Get system info") 
            print("  3. Power control")
            print("  4. Virtual media")
            print("  5. Boot configuration")
            print("  q. Quit")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == '1':
                await client.list_systems()
            elif choice == '2':
                system_id = input(f"System ID ({'/'.join(system_ids)}): ")
                if system_id in system_ids:
                    await client.get_system_info(system_id)
            elif choice == '3':
                system_id = input(f"System ID ({'/'.join(system_ids)}): ")
                if system_id in system_ids:
                    action = input("Action (On/Off/GracefulShutdown/ForceRestart): ")
                    await client.power_control(system_id, action)
            elif choice == '4':
                system_id = input(f"System ID ({'/'.join(system_ids)}): ")
                if system_id in system_ids:
                    await client.get_virtual_media(system_id)
            elif choice == '5':
                system_id = input(f"System ID ({'/'.join(system_ids)}): ")
                if system_id in system_ids:
                    boot_source = input("Boot source (Hdd/Cd/Pxe/None): ")
                    await client.set_boot_override(system_id, boot_source)
            else:
                print("Invalid choice")


def main():
    """Main entry point."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        return asyncio.run(interactive_mode())
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        return 0
    else:
        return asyncio.run(demo_basic_operations())


if __name__ == "__main__":
    sys.exit(main())
