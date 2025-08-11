#!/usr/bin/env python3
"""Generate OpenAPI JSON specification for HawkFish."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hawkfish_controller.main_app import create_app


def main():
    """Generate and save OpenAPI spec."""
    app = create_app()
    openapi_spec = app.openapi()
    
    # Ensure complete coverage of new endpoints
    paths = openapi_spec.get("paths", {})
    required_paths = [
        "/redfish/v1/",
        "/redfish/v1/Systems",
        "/redfish/v1/Systems/{system_id}",
        "/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset",
        "/redfish/v1/Oem/HawkFish/Profiles",
        "/redfish/v1/Oem/HawkFish/Batches", 
        "/redfish/v1/Oem/HawkFish/Images",
        "/redfish/v1/Oem/HawkFish/Hosts",
        "/redfish/v1/Oem/HawkFish/NetworkProfiles",
        "/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots",
        "/redfish/v1/UpdateService",
        "/redfish/v1/UpdateService/SoftwareInventory/{id}",
        "/redfish/v1/EventService/Subscriptions",
        "/redfish/v1/TaskService/Tasks",
    ]
    
    missing_paths = [path for path in required_paths if path not in paths]
    if missing_paths:
        print(f"Warning: Missing paths in OpenAPI spec: {missing_paths}", file=sys.stderr)
    
    # Write OpenAPI spec
    output_file = Path(__file__).parent.parent / "openapi.json"
    with open(output_file, "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    print(f"OpenAPI specification generated: {output_file}")
    print(f"Total paths: {len(paths)}")
    print(f"Total schemas: {len(openapi_spec.get('components', {}).get('schemas', {}))}")


if __name__ == "__main__":
    main()
