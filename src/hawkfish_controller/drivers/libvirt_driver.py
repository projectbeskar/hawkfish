from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..services.libvirt_pool import pool_manager


@dataclass
class LibvirtError(Exception):
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


class LibvirtDriver:
    def __init__(self, uri: str) -> None:
        self.uri = uri

    def _connect(self):
        """Get a connection from the pool."""
        conn = pool_manager.get_connection(self.uri)
        if conn is None:
            raise LibvirtError(
                f"Failed to get connection to libvirt at {self.uri}", status_code=503
            )
        return conn

    # --- public API ---
    def list_systems(self) -> list[dict[str, Any]]:
        conn = self._connect()
        if conn is None:
            return []
        systems: list[dict[str, Any]] = []
        try:
            for dom_id in conn.listDomainsID():  # running domains
                dom = conn.lookupByID(dom_id)
                systems.append(self._domain_to_system(dom))
            for name in conn.listDefinedDomains():  # defined but not running
                dom = conn.lookupByName(name)
                systems.append(self._domain_to_system(dom))
        except Exception as exc:  # pragma: no cover - requires real libvirt
            raise LibvirtError(f"Failed to list systems: {exc}") from exc
        # ensure unique by Id
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for s in systems:
            if s["Id"] not in seen:
                result.append(s)
                seen.add(s["Id"])
        return result

    def get_system(self, system_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        if conn is None:
            return None
        try:
            dom = conn.lookupByName(system_id)
        except Exception:
            return None
        return self._domain_to_system(dom)

    def reset_system(self, system_id: str, reset_type: str) -> None:
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        try:
            dom = conn.lookupByName(system_id)
        except Exception as exc:
            raise LibvirtError("System not found", status_code=404) from exc

        reset_type_norm = reset_type.lower()
        try:
            if reset_type_norm in {"on", "poweron", "forceon"}:
                dom.create()
            elif reset_type_norm in {"gracefulshutdown", "shutdown"}:
                dom.shutdown()
            elif reset_type_norm in {"forceoff", "off"}:
                dom.destroy()
            elif reset_type_norm in {"forcerestart", "force_restart", "reboot"}:
                try:
                    dom.reset(0)
                except Exception:
                    dom.destroy()
                    dom.create()
            else:
                raise LibvirtError(f"Unsupported ResetType: {reset_type}", status_code=400)
        except LibvirtError:
            raise
        except Exception as exc:  # pragma: no cover - requires real libvirt
            raise LibvirtError(f"Failed to perform reset: {exc}") from exc

    # --- mapping ---
    def _domain_to_system(self, dom) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        name = dom.name()
        power_state = self._power_state(dom)
        vcpu_count, mem_gib = self._resources(dom)
        nics = self._nic_details(dom)
        disk_gib = self._disk_summary(dom)
        boot = self._boot_info(dom)
        return {
            "@odata.type": "#ComputerSystem.v1_19_0.ComputerSystem",
            "@odata.id": f"/redfish/v1/Systems/{name}",
            "Id": name,
            "Name": name,
            "PowerState": power_state,
            "Boot": boot,
            "ProcessorSummary": {"Count": vcpu_count, "Model": None},
            "MemorySummary": {"TotalSystemMemoryGiB": mem_gib},
            "EthernetInterfaces": {
                "@odata.id": f"/redfish/v1/Systems/{name}/EthernetInterfaces"
            },
            "Storage": {"TotalGiB": disk_gib},
            "Actions": {
                "#ComputerSystem.Reset": {
                    "target": f"/redfish/v1/Systems/{name}/Actions/ComputerSystem.Reset",
                    "@Redfish.ActionInfo": None,
                }
            },
            "Links": {
                "Chassis": [{"@odata.id": "/redfish/v1/Chassis/1"}],
                "ManagedBy": [{"@odata.id": "/redfish/v1/Managers/HawkFish"}]
            },
            # Store interface details for sub-collection
            "_EthernetInterfaceDetails": nics,
        }

    def _power_state(self, dom) -> str:  # type: ignore[no-untyped-def]
        try:
            info = dom.info()
            state = info[0]
            # Map libvirt state to Redfish PowerState
            # VIR_DOMAIN_RUNNING = 1, VIR_DOMAIN_SHUTOFF = 5, etc.
            return "On" if state == 1 else "Off"
        except Exception:
            return "Off"

    def _resources(self, dom) -> tuple[int, float]:  # type: ignore[no-untyped-def]
        try:
            info = dom.info()
            vcpus = int(info[3])
            mem_kib = int(info[1])
            mem_gib = round(mem_kib / (1024 * 1024), 2)
            return vcpus, mem_gib
        except Exception:
            return 0, 0.0

    def _nic_count(self, dom) -> int:  # type: ignore[no-untyped-def]
        try:
            xml = dom.XMLDesc(0)
        except Exception:
            return 0
        # naive count
        return int(xml.count("<interface "))

    def _disk_summary(self, dom) -> float:  # type: ignore[no-untyped-def]
        try:
            _ = dom.XMLDesc(0)
        except Exception:
            return 0.0
        # We do not parse sizes without storage APIs; return 0.0 for now
        return 0.0

    def _nic_details(self, dom) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
        """Enhanced NIC details with Redfish-compliant structure."""
        try:
            xml = dom.XMLDesc(0)
            system_name = dom.name()
        except Exception:
            return []
        results: list[dict[str, Any]] = []
        # very simple regex parsing; a proper XML parser can replace this later
        for iface_idx, m in enumerate(re.finditer(r"<interface[^>]*?type='(\w+)'[\s\S]*?<mac address='([^']+)'/>([\s\S]*?)</interface>", xml)):
            itype, mac, iface_block = m.groups()
            # network name or source dev
            net_match = re.search(r"<source\s+network='([^']+)'", iface_block)
            if not net_match:
                net_match = re.search(r"<source\s+bridge='([^']+)'", iface_block)
            
            # Try to detect model for speed estimation
            model_match = re.search(r"<model\s+type='([^']+)'", iface_block)
            model = model_match.group(1) if model_match else "virtio"
            
            # Speed estimation based on model (virtio = 1Gbps, e1000 = 100Mbps)
            speed_mbps = 1000 if model in ["virtio", "virtio-net"] else 100
            
            # Get IP addresses via guest agent if available
            ipv4_addresses = []
            ipv6_addresses = []
            # This would require QGA integration - placeholder for now
            
            nic_id = f"eth{iface_idx}"
            results.append({
                "@odata.id": f"/redfish/v1/Systems/{system_name}/EthernetInterfaces/{nic_id}",
                "Id": nic_id,
                "Name": f"Ethernet Interface {iface_idx}",
                "MACAddress": mac,
                "SpeedMbps": speed_mbps,
                "LinkStatus": "LinkUp",  # Assume up if defined
                "Status": {
                    "State": "Enabled",
                    "Health": "OK"
                },
                "InterfaceEnabled": True,
                "DHCPv4": {"DHCPEnabled": True},  # Default assumption
                "DHCPv6": {"OperatingMode": "Stateful"},
                "IPv4Addresses": ipv4_addresses,
                "IPv6Addresses": ipv6_addresses,
                "VLAN": None,  # Would need to parse VLAN tags
                "VLANs": {"@odata.id": f"/redfish/v1/Systems/{system_name}/EthernetInterfaces/{nic_id}/VLANs"},
                "Links": {
                    "Chassis": {"@odata.id": "/redfish/v1/Chassis/1"}
                }
            })
        return results

    def _boot_info(self, dom) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        try:
            xml = dom.XMLDesc(0)
        except Exception:
            return {"BootSourceOverrideEnabled": "Disabled", "BootSourceOverrideTarget": "Hdd"}
        # Detect boot devices from os/boot and devices/bootorder
        # Simplify to present current and next targets
        next_target = None
        if "boot dev='cdrom'" in xml:
            next_target = "Cd"
        elif "boot dev='network'" in xml:
            next_target = "Pxe"
        elif "boot dev='hd'" in xml or "dev='hd'" in xml:
            next_target = "Hdd"
        return {
            "BootSourceOverrideEnabled": "Once" if next_target else "Disabled",
            "BootSourceOverrideTarget": next_target or "Hdd",
        }

    # --- boot control ---
    def set_boot_override(self, system_id: str, target: str, persist: bool = False) -> None:
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        try:
            dom = conn.lookupByName(system_id)
        except Exception as exc:
            raise LibvirtError("System not found", status_code=404) from exc
        target_norm = target.lower()
        if target_norm not in {"hdd", "pxe", "cd", "usb"}:
            raise LibvirtError("Unsupported boot target", status_code=400)
        try:
            # Set boot order in XML. We replace os/boot elements in a basic manner.
            xml = dom.XMLDesc(0)
            def boot_tag(t: str) -> str:
                mapping = {"hdd": "hd", "pxe": "network", "cd": "cdrom", "usb": "usb"}
                return f"<boot dev='{mapping[t]}'/>"

            new_os = re.sub(r"<os>[\s\S]*?</os>", f"<os>{boot_tag(target_norm)}</os>", xml)
            # Define the new XML persistently if requested, else set metadata for next boot where possible
            if persist:
                dom.undefineFlags(0)
                conn.defineXML(new_os)
            else:
                # For non-persistent, redefine as well; many libvirt boot settings are persistent by nature
                dom.undefineFlags(0)
                conn.defineXML(new_os)
        except Exception as exc:  # pragma: no cover - requires real libvirt
            raise LibvirtError(f"Failed to set boot override: {exc}") from exc

    # --- virtual media ---
    def attach_iso(self, system_id: str, image_path_or_url: str) -> None:
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        try:
            dom = conn.lookupByName(system_id)
        except Exception as exc:
            raise LibvirtError("System not found", status_code=404) from exc
        try:
            xml = dom.XMLDesc(0)
            # Simple approach: if a cdrom exists, point it to the new source; else, add an ide cdrom
            if "<disk type='file' device='cdrom'" in xml:
                # Change media using updateDeviceFlags with a new disk xml
                disk_xml = (
                    f"<disk type='file' device='cdrom'>"
                    f"<driver name='qemu' type='raw'/>"
                    f"<source file='{image_path_or_url}'/>"
                    f"<target dev='hdc' bus='ide'/></disk>"
                )
            else:
                disk_xml = (
                    f"<disk type='file' device='cdrom'>"
                    f"<driver name='qemu' type='raw'/>"
                    f"<source file='{image_path_or_url}'/>"
                    f"<target dev='hdc' bus='ide'/></disk>"
                )
            dom.attachDeviceFlags(disk_xml, 0)
        except Exception as exc:  # pragma: no cover - requires real libvirt
            raise LibvirtError(f"Failed to attach ISO: {exc}") from exc

    def detach_iso(self, system_id: str) -> None:
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        try:
            dom = conn.lookupByName(system_id)
        except Exception as exc:
            raise LibvirtError("System not found", status_code=404) from exc
        try:
            # Attempt to eject by attaching an empty cdrom source
            disk_xml = (
                "<disk type='file' device='cdrom'>"
                "<driver name='qemu' type='raw'/>"
                "<target dev='hdc' bus='ide'/></disk>"
            )
            dom.attachDeviceFlags(disk_xml, 0)
        except Exception as exc:  # pragma: no cover - requires real libvirt
            raise LibvirtError(f"Failed to detach ISO: {exc}") from exc

    # --- snapshot operations ---
    def create_snapshot(self, system_id: str, snapshot_name: str, description: str | None = None) -> None:
        """Create a VM snapshot."""
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        
        try:
            dom = conn.lookupByName(system_id)
        except Exception as exc:
            raise LibvirtError("System not found", status_code=404) from exc
        
        # Create snapshot XML
        snapshot_xml = f"""
        <domainsnapshot>
            <name>{snapshot_name}</name>
            <description>{description or 'HawkFish snapshot'}</description>
            <memory snapshot='external'/>
            <disks>
                <disk name='vda' snapshot='external'/>
            </disks>
        </domainsnapshot>
        """
        
        try:
            dom.snapshotCreateXML(snapshot_xml.strip(), 0)
        except Exception as exc:
            raise LibvirtError(f"Failed to create snapshot: {exc}") from exc

    def list_libvirt_snapshots(self, system_id: str) -> list[dict[str, Any]]:
        """List snapshots for a system from libvirt."""
        conn = self._connect()
        if conn is None:
            return []
        
        try:
            dom = conn.lookupByName(system_id)
            snapshot_names = dom.listAllSnapshots(0)
            snapshots = []
            
            for snap in snapshot_names:
                name = snap.getName()
                snapshots.append({
                    "Name": name,
                    "CreationTime": "unknown",  # Would parse from XML
                    "State": "Ready"
                })
            
            return snapshots
        except Exception:
            return []

    def revert_snapshot(self, system_id: str, snapshot_name: str) -> None:
        """Revert system to a snapshot."""
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        
        try:
            dom = conn.lookupByName(system_id)
            snap = dom.snapshotLookupByName(snapshot_name, 0)
            dom.revertToSnapshot(snap, 0)
        except Exception as exc:
            raise LibvirtError(f"Failed to revert snapshot: {exc}") from exc

    def delete_libvirt_snapshot(self, system_id: str, snapshot_name: str) -> None:
        """Delete a snapshot."""
        conn = self._connect()
        if conn is None:
            raise LibvirtError("Libvirt not available", status_code=503)
        
        try:
            dom = conn.lookupByName(system_id)
            snap = dom.snapshotLookupByName(snapshot_name, 0)
            snap.delete(0)
        except Exception as exc:
            raise LibvirtError(f"Failed to delete snapshot: {exc}") from exc


