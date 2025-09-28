#!/usr/bin/env python3
"""
HPE iLO BIOS configuration workflow example.

This script demonstrates BIOS configuration staging and application
using only HPE iLO-compatible endpoints.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any

import httpx


class IloBiosWorkflow:
    """HPE iLO BIOS configuration workflow."""
    
    def __init__(self, base_url: str, token: str, system_id: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.system_id = system_id
        self.client = httpx.AsyncClient(verify=False)
        
    def _headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        return {
            "Content-Type": "application/json",
            "X-Auth-Token": self.token
        }
    
    async def get_current_bios_settings(self) -> dict[str, Any]:
        """Get current BIOS settings."""
        print("📋 Getting current BIOS settings...")
        
        response = await self.client.get(
            f"{self.base_url}/redfish/v1/Systems/{self.system_id}/Bios",
            headers=self._headers()
        )
        response.raise_for_status()
        
        data = response.json()
        attributes = data.get("Attributes", {})
        pending = data.get("Oem", {}).get("Hpe", {}).get("PendingChanges", False)
        
        print(f"   Boot Mode: {attributes.get('BootMode', 'Unknown')}")
        print(f"   Secure Boot: {attributes.get('SecureBoot', 'Unknown')}")
        print(f"   Boot Order: {attributes.get('PersistentBootConfigOrder', [])}")
        print(f"   Pending Changes: {pending}")
        
        return data
    
    async def stage_bios_changes(self, changes: dict[str, Any], apply_time: str = "OnReset") -> bool:
        """Stage BIOS changes with specified apply time."""
        print(f"⚙️ Staging BIOS changes (ApplyTime={apply_time})...")
        
        payload = {
            "Attributes": changes,
            "Oem": {
                "Hpe": {
                    "ApplyTime": apply_time
                }
            }
        }
        
        print(f"   Changes: {json.dumps(changes, indent=2)}")
        
        try:
            response = await self.client.patch(
                f"{self.base_url}/redfish/v1/Systems/{self.system_id}/Bios/Settings",
                headers=self._headers(),
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            task_state = result.get("TaskState", "Unknown")
            message = result.get("Message", "")
            
            print(f"   ✅ Task State: {task_state}")
            print(f"   Message: {message}")
            
            return task_state in ["Completed", "Pending"]
            
        except httpx.HTTPStatusError as e:
            print(f"   ❌ Error: {e.response.status_code}")
            
            try:
                error_detail = e.response.json()
                if "error" in error_detail and "@Message.ExtendedInfo" in error_detail["error"]:
                    extended_info = error_detail["error"]["@Message.ExtendedInfo"][0]
                    print(f"   Message: {extended_info.get('Message', 'Unknown error')}")
                    print(f"   Resolution: {extended_info.get('Resolution', 'No resolution provided')}")
                else:
                    print(f"   Detail: {error_detail}")
            except Exception:
                print(f"   Response: {e.response.text}")
            
            return False
    
    async def reset_system(self, reset_type: str = "ForceRestart") -> bool:
        """Reset the system to apply pending BIOS changes."""
        print(f"🔄 Resetting system ({reset_type})...")
        
        payload = {"ResetType": reset_type}
        
        try:
            response = await self.client.post(
                f"{self.base_url}/redfish/v1/Systems/{self.system_id}/Actions/ComputerSystem.Reset",
                headers=self._headers(),
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            task_state = result.get("TaskState", "Unknown")
            
            print(f"   ✅ Reset initiated: {task_state}")
            return task_state == "Completed"
            
        except httpx.HTTPStatusError as e:
            print(f"   ❌ Reset failed: {e.response.status_code}")
            print(f"   Detail: {e.response.text}")
            return False
    
    async def wait_for_no_pending_changes(self, timeout_seconds: int = 30) -> bool:
        """Wait for pending BIOS changes to be applied."""
        print("⏳ Waiting for BIOS changes to be applied...")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            data = await self.get_current_bios_settings()
            pending = data.get("Oem", {}).get("Hpe", {}).get("PendingChanges", False)
            
            if not pending:
                print("   ✅ BIOS changes applied successfully")
                return True
            
            print("   ⏳ Still pending, waiting...")
            await asyncio.sleep(2)
        
        print("   ⚠️ Timeout waiting for BIOS changes")
        return False
    
    async def demo_workflow(self):
        """Run complete BIOS configuration workflow."""
        print("🎭 HPE iLO BIOS Configuration Workflow")
        print("=" * 50)
        print(f"System: {self.system_id}")
        print(f"Time: {datetime.now().isoformat()}")
        print()
        
        try:
            # Step 1: Get current settings
            await self.get_current_bios_settings()
            print()
            
            # Step 2: Stage UEFI + SecureBoot changes
            changes = {
                "BootMode": "Uefi",
                "SecureBoot": "Enabled",
                "PersistentBootConfigOrder": ["Cd", "Pxe", "Hdd"]
            }
            
            success = await self.stage_bios_changes(changes, "OnReset")
            if not success:
                print("❌ Failed to stage BIOS changes")
                return False
            print()
            
            # Step 3: Verify changes are pending
            data = await self.get_current_bios_settings()
            pending = data.get("Oem", {}).get("Hpe", {}).get("PendingChanges", False)
            
            if not pending:
                print("⚠️ Expected pending changes, but none found")
                return False
            print()
            
            # Step 4: Apply changes via system reset
            success = await self.reset_system("ForceRestart")
            if not success:
                print("❌ Failed to reset system")
                return False
            print()
            
            # Step 5: Wait for changes to be applied
            success = await self.wait_for_no_pending_changes()
            if not success:
                print("⚠️ Changes may not have been applied")
            print()
            
            # Step 6: Verify final state
            print("🎯 Final BIOS configuration:")
            await self.get_current_bios_settings()
            
            print()
            print("✅ BIOS workflow completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            return False
        
        finally:
            await self.client.aclose()
    
    async def demo_validation_errors(self):
        """Demonstrate BIOS validation error handling."""
        print("🧪 HPE iLO BIOS Validation Error Examples")
        print("=" * 50)
        
        try:
            # Test 1: Invalid BootMode
            print("Test 1: Invalid BootMode")
            await self.stage_bios_changes({"BootMode": "InvalidMode"})
            print()
            
            # Test 2: SecureBoot with LegacyBios
            print("Test 2: SecureBoot with LegacyBios (should fail)")
            await self.stage_bios_changes({
                "BootMode": "LegacyBios",
                "SecureBoot": "Enabled"
            })
            print()
            
            # Test 3: Invalid boot device
            print("Test 3: Invalid boot device")
            await self.stage_bios_changes({
                "PersistentBootConfigOrder": ["Cd", "InvalidDevice", "Hdd"]
            })
            print()
            
            # Test 4: ApplyTime=Immediate with reboot required
            print("Test 4: ApplyTime=Immediate (should require OnReset)")
            await self.stage_bios_changes({
                "BootMode": "LegacyBios"
            }, apply_time="Immediate")
            print()
            
        finally:
            await self.client.aclose()


async def main():
    """Main entry point."""
    import os
    
    base_url = os.getenv("HAWKFISH_URL", "https://localhost:8080")
    token = os.getenv("HAWKFISH_TOKEN")
    system_id = os.getenv("SYSTEM_ID", "vm-001")
    
    if not token:
        print("❌ HAWKFISH_TOKEN environment variable required")
        return 1
    
    workflow = IloBiosWorkflow(base_url, token, system_id)
    
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        await workflow.demo_validation_errors()
    else:
        success = await workflow.demo_workflow()
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
