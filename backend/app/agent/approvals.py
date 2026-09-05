from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ToolRiskLevel(StrEnum):
    SAFE = "safe"
    WRITE = "write"
    HARDWARE = "hardware"
    DANGEROUS = "dangerous"


@dataclass(frozen=True)
class ToolApprovalRule:
    tool_name: str
    risk_level: ToolRiskLevel
    requires_approval: bool
    writes_files: bool
    uses_hardware: bool
    timeout_seconds: int
    description: str


# Comprehensive, centralized tool governance policy.
_POLICY_RULES: dict[str, ToolApprovalRule] = {
    # Safe tools (Read / Inspect / Search / Compile / Validate)
    "read_file": ToolApprovalRule("read_file", ToolRiskLevel.SAFE, False, False, False, 10, "Read workspace file"),
    "list_files": ToolApprovalRule("list_files", ToolRiskLevel.SAFE, False, False, False, 10, "List files in directory"),
    "search_code": ToolApprovalRule("search_code", ToolRiskLevel.SAFE, False, False, False, 15, "Search codebase for pattern"),
    "retrieve_knowledge": ToolApprovalRule("retrieve_knowledge", ToolRiskLevel.SAFE, False, False, False, 15, "Retrieve embedded knowledge documentation"),
    "get_skill": ToolApprovalRule("get_skill", ToolRiskLevel.SAFE, False, False, False, 5, "Get peripheral skill definition"),
    "get_pin_info": ToolApprovalRule("get_pin_info", ToolRiskLevel.SAFE, False, False, False, 5, "Query MCU pin multiplexing info"),
    "get_mcu_info": ToolApprovalRule("get_mcu_info", ToolRiskLevel.SAFE, False, False, False, 5, "Query MCU architecture and memory limits"),
    "compile_project": ToolApprovalRule("compile_project", ToolRiskLevel.SAFE, False, False, False, 120, "Compile project with native toolchain"),
    "validate_project": ToolApprovalRule("validate_project", ToolRiskLevel.SAFE, False, False, False, 30, "Run static peripheral and AST validations"),
    "clangd_diagnostics": ToolApprovalRule("clangd_diagnostics", ToolRiskLevel.SAFE, False, False, False, 30, "Query LSP compiler diagnostics"),
    "cppcheck_project": ToolApprovalRule("cppcheck_project", ToolRiskLevel.SAFE, False, False, False, 60, "Run static security and memory analysis"),
    "read_register": ToolApprovalRule("read_register", ToolRiskLevel.SAFE, False, False, False, 10, "Query hardware register map definition"),
    "read_symbol": ToolApprovalRule("read_symbol", ToolRiskLevel.SAFE, False, False, False, 10, "Inspect ELF binary symbol address and size"),

    # Write tools (Workspace file mutations)
    "apply_patch": ToolApprovalRule("apply_patch", ToolRiskLevel.WRITE, True, True, False, 30, "Apply targeted code patch to workspace file"),
    "write_file": ToolApprovalRule("write_file", ToolRiskLevel.WRITE, True, True, False, 30, "Write or overwrite file in workspace"),
    "create_project": ToolApprovalRule("create_project", ToolRiskLevel.WRITE, True, True, False, 30, "Create new project from platform template"),
    "register_hal_module": ToolApprovalRule("register_hal_module", ToolRiskLevel.WRITE, True, True, False, 30, "Enable peripheral HAL module and update build"),
    "configure_gpio": ToolApprovalRule("configure_gpio", ToolRiskLevel.WRITE, True, True, False, 30, "Generate GPIO configuration code"),
    "configure_usart": ToolApprovalRule("configure_usart", ToolRiskLevel.WRITE, True, True, False, 30, "Generate USART configuration code"),
    "configure_adc": ToolApprovalRule("configure_adc", ToolRiskLevel.WRITE, True, True, False, 30, "Generate ADC configuration code"),
    "configure_pwm": ToolApprovalRule("configure_pwm", ToolRiskLevel.WRITE, True, True, False, 30, "Generate PWM timer configuration code"),
    "configure_i2c": ToolApprovalRule("configure_i2c", ToolRiskLevel.WRITE, True, True, False, 30, "Generate I2C configuration code"),
    "configure_spi": ToolApprovalRule("configure_spi", ToolRiskLevel.WRITE, True, True, False, 30, "Generate SPI configuration code"),
    "configure_exti": ToolApprovalRule("configure_exti", ToolRiskLevel.WRITE, True, True, False, 30, "Generate EXTI interrupt configuration code"),

    # Hardware tools (Physical probe / serial interactions)
    "flash_firmware": ToolApprovalRule("flash_firmware", ToolRiskLevel.HARDWARE, True, False, True, 60, "Flash firmware ELF to target MCU via probe"),
    "reset_device": ToolApprovalRule("reset_device", ToolRiskLevel.HARDWARE, True, False, True, 20, "Trigger physical target MCU reset via probe"),
    "serial_sample": ToolApprovalRule("serial_sample", ToolRiskLevel.HARDWARE, False, False, True, 30, "Capture serial port stream and check markers"),
    "run_hardware": ToolApprovalRule("run_hardware", ToolRiskLevel.HARDWARE, True, False, True, 90, "Execute closed-loop build, flash, serial test"),
    "auto_debug": ToolApprovalRule("auto_debug", ToolRiskLevel.HARDWARE, True, True, True, 120, "Run automated hardware fault diagnosis and patch"),

    # Dangerous tools (Reserved irreversible hardware operations - NEVER run automatically)
    "erase_flash": ToolApprovalRule("erase_flash", ToolRiskLevel.DANGEROUS, True, False, True, 60, "Mass erase microcontroller flash memory"),
    "mass_erase": ToolApprovalRule("mass_erase", ToolRiskLevel.DANGEROUS, True, False, True, 60, "Full chip unprotect and mass erase"),
    "burn_efuse": ToolApprovalRule("burn_efuse", ToolRiskLevel.DANGEROUS, True, False, True, 30, "Permanently burn one-time programmable eFuses"),
    "set_option_bytes": ToolApprovalRule("set_option_bytes", ToolRiskLevel.DANGEROUS, True, False, True, 30, "Write hardware Option Bytes or flash read protection"),
}


class ApprovalPolicyManager:
    @staticmethod
    def get_rule(tool_name: str) -> ToolApprovalRule:
        return _POLICY_RULES.get(
            tool_name,
            ToolApprovalRule(
                tool_name=tool_name,
                risk_level=ToolRiskLevel.WRITE,
                requires_approval=True,
                writes_files=True,
                uses_hardware=False,
                timeout_seconds=30,
                description=f"Generic tool {tool_name}",
            ),
        )

    @classmethod
    def check_authorization(cls, tool_name: str, mode: str = "auto", user_approved: bool = False) -> tuple[bool, bool, str]:
        """Returns (allowed, requires_approval, reason)."""
        rule = cls.get_rule(tool_name)
        if rule.risk_level == ToolRiskLevel.SAFE:
            return True, False, "Safe operation automatically allowed"
        if rule.risk_level == ToolRiskLevel.DANGEROUS:
            if not user_approved:
                return False, True, f"Dangerous irreversible operation {tool_name} strictly requires explicit user approval"
            return True, False, "Dangerous operation explicitly approved by user"
        if rule.risk_level in {ToolRiskLevel.WRITE, ToolRiskLevel.HARDWARE}:
            if mode == "auto":
                return True, False, f"Mode is auto: {rule.risk_level.value} operation allowed"
            if not user_approved:
                return False, True, f"Mode is {mode}: {rule.risk_level.value} operation requires user confirmation"
            return True, False, "Operation approved"
        return True, False, "Allowed"
