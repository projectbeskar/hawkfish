#!/usr/bin/env python3
"""
Example HawkFish Python client using the generated SDK.

This demonstrates basic operations using the HawkFish Redfish API.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

import httpx


class HawkFishClient:
    """Simple HawkFish client for demonstration purposes."""
    
    def __init__(self, base_url: str, username: str = "local", password: str = ""):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session_token: str | None = None
        self.client = httpx.AsyncClient(verify=False)  # For dev with self-signed certs
    
    async def __aenter__(self):
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self) -> None:
        """Authenticate and get session token."""
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/SessionService/Sessions",
            json={"UserName": self.username, "Password": self.password}
        )
        response.raise_for_status()
        data = response.json()
        self.session_token = data["SessionToken"]
        print(f"✓ Authenticated as {self.username}")
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["X-Auth-Token"] = self.session_token
        return headers
    
    async def get_service_root(self) -> Dict[str, Any]:
        """Get service root information."""
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_systems(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """List all systems."""
        params = {"page": page, "per_page": per_page}
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def get_system(self, system_id: str) -> Dict[str, Any]:
        """Get specific system details."""
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems/{system_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def power_action(self, system_id: str, reset_type: str) -> None:
        """Perform power action on system."""
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset",
            headers=self._headers(),
            json={"ResetType": reset_type}
        )
        response.raise_for_status()
        print(f"✓ Power action '{reset_type}' sent to system {system_id}")
    
    async def create_system_from_profile(self, profile_id: str, name: str) -> str:
        """Create a system from a profile."""
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Systems",
            headers=self._headers(),
            json={"Name": name, "ProfileId": profile_id}
        )
        if response.status_code == 202:
            # Long-running operation, get task ID
            location = response.headers.get("Location", "")
            task_id = location.split("/")[-1] if location else "unknown"
            print(f"✓ System creation task started: {task_id}")
            return task_id
        else:
            response.raise_for_status()
            return response.json().get("Id", "")
    
    async def list_profiles(self) -> List[Dict[str, Any]]:
        """List available profiles."""
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Oem/HawkFish/Profiles",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json().get("Members", [])
    
    async def create_profile(self, profile_spec: Dict[str, Any]) -> str:
        """Create a new profile."""
        response = await self.client.post(
            f"{self.base_url}/redfish/v1/Oem/HawkFish/Profiles",
            headers=self._headers(),
            json=profile_spec
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Profile created: {data['Id']}")
        return data["Id"]
    
    async def list_images(self) -> List[Dict[str, Any]]:
        """List available images."""
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Oem/HawkFish/Images",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json().get("Members", [])
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/TaskService/Tasks/{task_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()


async def demo_workflow():
    """Demonstrate a complete HawkFish workflow."""
    base_url = "http://localhost:8080"
    
    print("🚀 HawkFish Python Client Demo")
    print("=" * 40)
    
    try:
        async with HawkFishClient(base_url) as client:
            # Get service information
            service_root = await client.get_service_root()
            print(f"📊 Connected to HawkFish {service_root.get('Id', 'Unknown')}")
            
            # List systems
            systems_data = await client.list_systems()
            systems = systems_data.get("Members", [])
            print(f"💻 Found {len(systems)} systems")
            
            # Show system details
            for system in systems[:3]:  # Show first 3
                system_id = system["Id"]
                details = await client.get_system(system_id)
                power_state = details.get("PowerState", "Unknown")
                print(f"  - {system_id}: {power_state}")
            
            # List profiles
            profiles = await client.list_profiles()
            print(f"📋 Found {len(profiles)} profiles")
            for profile in profiles[:3]:
                print(f"  - {profile['Id']}: {profile.get('Name', 'Unnamed')}")
            
            # Create a simple profile if none exist
            if not profiles:
                print("🔧 Creating example profile...")
                profile_spec = {
                    "Name": "demo-small",
                    "CPU": 2,
                    "MemoryMiB": 2048,
                    "DiskGiB": 20,
                    "Network": "default",
                    "Boot": {"Primary": "Hdd"}
                }
                profile_id = await client.create_profile(profile_spec)
                
                # Create a system from the profile
                print("🖥️  Creating system from profile...")
                task_id = await client.create_system_from_profile(profile_id, "demo-vm-001")
                
                # Poll task status
                for i in range(10):
                    await asyncio.sleep(2)
                    task = await client.get_task(task_id)
                    state = task.get("TaskState", "Unknown")
                    percent = task.get("PercentComplete", 0)
                    print(f"  Task {task_id}: {state} ({percent}%)")
                    
                    if state in ("Completed", "Exception"):
                        break
            
            # List images
            images = await client.list_images()
            print(f"💿 Found {len(images)} images")
            for image in images[:3]:
                print(f"  - {image['Id']}: {image.get('Name', 'Unnamed')} v{image.get('Version', '?')}")
            
            print("\n✅ Demo completed successfully!")
            
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        sys.exit(0)
    
    asyncio.run(demo_workflow())
