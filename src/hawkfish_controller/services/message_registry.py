"""
HPE-compatible message registry for error messages and events.
"""

from typing import Any


class HpeMessageRegistry:
    """HPE-compatible message registry for error messages."""
    
    # HPE Message Registry entries
    MESSAGES = {
        "Oem.Hpe.Bios.InvalidAttribute": {
            "Description": "Invalid BIOS attribute value specified.",
            "Message": "The BIOS attribute '%1' has an invalid value '%2'.",
            "NumberOfArgs": 2,
            "ParamTypes": ["string", "string"],
            "Resolution": "Check the attribute name and value against the BIOS registry.",
            "Severity": "Warning"
        },
        "Oem.Hpe.Bios.RequiresPowerOff": {
            "Description": "The requested BIOS changes require the system to be powered off.",
            "Message": "The requested BIOS setting changes require ApplyTime=OnReset or system power off.",
            "NumberOfArgs": 0,
            "ParamTypes": [],
            "Resolution": "Set ApplyTime to OnReset or power off the system before applying changes.",
            "Severity": "Warning"
        },
        "Oem.Hpe.Bios.RequiresUefiForSecureBoot": {
            "Description": "SecureBoot requires UEFI boot mode.",
            "Message": "SecureBoot can only be enabled when BootMode is set to Uefi.",
            "NumberOfArgs": 0,
            "ParamTypes": [],
            "Resolution": "Set BootMode to Uefi before enabling SecureBoot.",
            "Severity": "Warning"
        },
        "Oem.Hpe.Bios.TemplateUnavailable": {
            "Description": "UEFI firmware template unavailable.",
            "Message": "The UEFI firmware template for SecureBoot is not available.",
            "NumberOfArgs": 0,
            "ParamTypes": [],
            "Resolution": "Ensure UEFI firmware templates are installed and accessible.",
            "Severity": "Critical"
        },
        "Oem.Hpe.Media.DeviceUnavailable": {
            "Description": "Virtual media device unavailable.",
            "Message": "The virtual media device '%1' is not available or busy.",
            "NumberOfArgs": 1,
            "ParamTypes": ["string"],
            "Resolution": "Check device status and try again.",
            "Severity": "Warning"
        },
        "Oem.Hpe.Console.SessionLimitExceeded": {
            "Description": "Console session limit exceeded.",
            "Message": "Maximum number of console sessions (%1) exceeded.",
            "NumberOfArgs": 1,
            "ParamTypes": ["number"],
            "Resolution": "Close existing console sessions before creating new ones.",
            "Severity": "Warning"
        },
        "Oem.Hpe.Console.ProtocolNotSupported": {
            "Description": "Console protocol not supported.",
            "Message": "Console protocol '%1' is not supported.",
            "NumberOfArgs": 1,
            "ParamTypes": ["string"],
            "Resolution": "Use a supported console protocol (VNC, Serial).",
            "Severity": "Warning"
        },
        "Oem.Hpe.General.Conflict": {
            "Description": "Resource conflict detected.",
            "Message": "The requested operation conflicts with the current state of '%1'.",
            "NumberOfArgs": 1,
            "ParamTypes": ["string"],
            "Resolution": "Check resource state and resolve conflicts before retrying.",
            "Severity": "Warning"
        }
    }
    
    @classmethod
    def get_message(cls, message_id: str, args: list[Any] = None) -> dict[str, Any]:
        """Get formatted message with arguments."""
        if message_id not in cls.MESSAGES:
            return {
                "MessageId": "Base.1.0.GeneralError",
                "Message": f"Unknown message ID: {message_id}",
                "Severity": "Critical",
                "Resolution": "Contact system administrator."
            }
        
        template = cls.MESSAGES[message_id]
        message = template["Message"]
        
        # Replace argument placeholders
        if args:
            for i, arg in enumerate(args, 1):
                message = message.replace(f'%{i}', str(arg))
        
        return {
            "MessageId": message_id,
            "Message": message,
            "Severity": template["Severity"],
            "Resolution": template["Resolution"]
        }
    
    @classmethod
    def create_extended_info(cls, message_id: str, args: list[Any] = None) -> list[dict[str, Any]]:
        """Create ExtendedInfo array with HPE message."""
        return [cls.get_message(message_id, args)]


# Global registry instance
hpe_message_registry = HpeMessageRegistry()
