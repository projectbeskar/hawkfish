from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class LibvirtError(Exception):
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


class LibvirtDriver:
    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._libvirt = None
        self._conn = None

    # --- libvirt helpers ---
    def _ensure_import(self) -> None:
        if self._libvirt is None:
            try:
                import libvirt  # type: ignore

                self._libvirt = libvirt
            except Exception:  # pragma: no cover - environment-dependent
                self._libvirt = None

    def _connect(self):
        self._ensure_import()
        if self._libvirt is None:
            # Running without libvirt bindings; behave as no systems
            return None
        if self._conn is not None:
            return self._conn
        try:
            self._conn = self._libvirt.open(self.uri)
            return self._conn
        except Exception as exc:  # pragma: no cover - requires real libvirt
            raise LibvirtError(
                f"Failed to connect to libvirt at {self.uri}: {exc}", status_code=503
            ) from exc

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
        nic_count = self._nic_count(dom)
        nics = self._nic_details(dom)
        disk_gib = self._disk_summary(dom)
        boot = self._boot_info(dom)
        return {
            "@odata.id": f"/redfish/v1/Systems/{name}",
            "Id": name,
            "Name": name,
            "PowerState": power_state,
            "Boot": boot,
            "ProcessorSummary": {"Count": vcpu_count, "Model": None},
            "MemorySummary": {"TotalSystemMemoryGiB": mem_gib},
            "EthernetInterfaces": {"Count": nic_count, "Interfaces": nics},
            "Storage": {"TotalGiB": disk_gib},
            "Actions": {
                "#ComputerSystem.Reset": {
                    "target": f"/redfish/v1/Systems/{name}/Actions/ComputerSystem.Reset",
                    "@Redfish.ActionInfo": None,
                }
            },
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
        try:
            xml = dom.XMLDesc(0)
        except Exception:
            return []
        results: list[dict[str, Any]] = []
        # very simple regex parsing; a proper XML parser can replace this later
        for m in re.finditer(r"<interface[^>]*?type='(\w+)'[\s\S]*?<mac address='([^']+)'/>([\s\S]*?)</interface>", xml):
            _itype, mac, iface_block = m.groups()
            # network name or source dev
            net_match = re.search(r"<source\s+network='([^']+)'", iface_block)
            if not net_match:
                net_match = re.search(r"<source\s+bridge='([^']+)'", iface_block)
            network = net_match.group(1) if net_match else None
            results.append({"MACAddress": mac, "Network": network})
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


