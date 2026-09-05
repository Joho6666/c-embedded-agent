from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.mcu.stm32f103 import get_mcu_info, get_pin_info, load_board
from app.platforms.base import DetectionEvidence, LineCallback, PlatformAdapter, PlatformDescriptor, PlatformResult
from app.tools.compiler import CompileError, compile_project, compile_project_streaming
from app.tools.flash import ALLOWED_INTERFACE, ALLOWED_TARGET, FlashError, detect_chip_id, flash_elf
from app.tools.hardware_run import auto_debug as stm32_auto_debug, run_pipeline, sample_serial
from app.tools.ioc import parse_ioc
from app.tools.hal_modules import register_hal_module
from app.tools.periph_gen import configure_peripheral
from app.tools.serialutil import list_ports
from app.tools.toolchain import prepend_toolchain_path
from app.validation import hardware_status, select_validators, validate_project


class Stm32F103Adapter(PlatformAdapter):
    descriptor = PlatformDescriptor(
        adapter_id="stm32f103-hal",
        name="STM32F103 HAL",
        platform="STM32",
        mcu="STM32F103C8T6",
        framework="HAL",
        status="ready",
        boards=("bluepill_f103c8",),
        toolchains=("ARM_GCC", "make"),
        capabilities=(
            "detect",
            "create",
            "context",
            "build",
            "clean",
            "flash",
            "reset",
            "serial",
            "generate",
            "validate",
            "hardware",
        ),
    )

    @property
    def template_path(self) -> Path:
        return self.repo_root / "templates" / "stm32f103_hal_official"

    @property
    def protected_paths(self) -> tuple[str, ...]:
        return (
            ".git",
            "project.json",
            "STM32F103C8Tx_FLASH.ld",
            "startup_stm32f103xb.s",
            "Drivers/CMSIS",
        )

    @property
    def tools(self) -> tuple[str, ...]:
        return (
            "compile_project",
            "flash_firmware",
            "serial_sample",
            "run_hardware",
            "configure_usart",
            "configure_adc",
            "configure_pwm",
            "configure_i2c",
            "configure_spi",
            "configure_exti",
            "validate_project",
        )

    @property
    def skills(self) -> tuple[str, ...]:
        return ("stm32f103",)

    @property
    def validators(self) -> tuple[str, ...]:
        return ("gpio", "exti", "usart", "dma", "adc", "pwm", "tim", "i2c", "spi", "review")

    @property
    def knowledge_roots(self) -> tuple[Path, ...]:
        return (self.repo_root / "knowledge_sources" / "stm32f103",)

    def detect_project(self, root: Path) -> DetectionEvidence:
        root = Path(root)
        reasons: list[str] = []
        conflicts: list[str] = []
        confidence = 0.0

        project = _read_json(root / "project.json")
        if project:
            adapter_id = _norm(project.get("adapterId"))
            platform = _norm(project.get("platform"))
            mcu = _norm(project.get("mcu"))
            if adapter_id and adapter_id != _norm(self.adapter_id):
                conflicts.append(f"project.json selects adapter {project.get('adapterId')}")
            elif adapter_id == _norm(self.adapter_id):
                reasons.append("project.json selects stm32f103-hal")
                confidence = max(confidence, 0.98)
            if mcu and "stm32f4" in mcu:
                conflicts.append(f"unsupported STM32 family in project.json: {project.get('mcu')}")
            elif mcu and "stm32f103" in mcu:
                reasons.append("project.json identifies STM32F103")
                confidence = max(confidence, 0.95)
            elif platform == "stm32" and not mcu:
                reasons.append("project.json identifies STM32 without an MCU")
                confidence = max(confidence, 0.45)

        for ioc in sorted(root.glob("*.ioc")):
            text = _read_text(ioc)
            low = text.lower()
            if "stm32f4" in low or "mcu.family=stm32f4" in low:
                conflicts.append(f"{ioc.name} identifies unsupported STM32F4")
            elif "stm32f103" in low or "mcu.family=stm32f1" in low:
                reasons.append(f"{ioc.name} identifies STM32F103/STM32F1")
                confidence = max(confidence, 1.0)

        signatures = (
            root / "Drivers" / "STM32F1xx_HAL_Driver",
            root / "STM32F103C8Tx_FLASH.ld",
            root / "startup_stm32f103xb.s",
        )
        found = [p.relative_to(root).as_posix() for p in signatures if p.exists()]
        if found:
            reasons.append("F103 project signatures: " + ", ".join(found))
            confidence = max(confidence, 0.85 if len(found) >= 2 else 0.65)
        if (root / "Drivers" / "STM32F4xx_HAL_Driver").exists() or any(root.glob("*STM32F4*.ld")):
            conflicts.append("STM32F4 project signatures found")
        cmake = _read_text(root / "CMakeLists.txt")
        sdkconfig = _read_text(root / "sdkconfig") + _read_text(root / "sdkconfig.defaults")
        if ("IDF_PATH" in cmake and "project.cmake" in cmake) or "CONFIG_IDF_TARGET" in sdkconfig:
            conflicts.append("ESP-IDF project signatures found")

        matched = confidence >= 0.6 and not conflicts
        return DetectionEvidence(self.adapter_id, matched, confidence if matched else 0.0, tuple(reasons), tuple(conflicts))

    def create_template(
        self,
        destination: Path,
        *,
        name: str,
        board: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlatformResult:
        chosen_board = board or "bluepill_f103c8"
        if chosen_board not in self.descriptor.boards:
            return PlatformResult(status="FAIL", operation="create", adapter_id=self.adapter_id, reason=f"unsupported board: {chosen_board}")
        if not self.template_path.is_dir():
            return PlatformResult(status="FAIL", operation="create", adapter_id=self.adapter_id, reason=f"template missing: {self.template_path}")
        try:
            self.copy_template(self.template_path, Path(destination))
            meta = {
                **dict(metadata or {}),
                "name": name,
                "platform": self.descriptor.platform,
                "mcu": self.descriptor.mcu,
                "framework": self.descriptor.framework,
                "toolchain": "ARM_GCC",
                "board": "Blue Pill",
                "boardId": chosen_board,
                "led": "PC13",
                "adapterId": self.adapter_id,
                "capabilities": list(self.descriptor.capabilities),
            }
            (Path(destination) / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            return PlatformResult("PASS", "create", self.adapter_id, {"path": str(destination), "metadata": meta})
        except (OSError, FileExistsError) as exc:
            return PlatformResult(status="FAIL", operation="create", adapter_id=self.adapter_id, reason=str(exc))

    def load_context(self, root: Path) -> dict[str, Any]:
        root = Path(root)
        defaults = get_mcu_info()
        facts: dict[str, Any] = {
            "platform": self.descriptor.platform,
            "adapterId": self.adapter_id,
            "framework": self.descriptor.framework,
            "mcu": defaults.get("name"),
            "core": defaults.get("core"),
            "clockMHz": defaults.get("clock_mhz"),
            "flashKb": defaults.get("flash_kb"),
            "ramKb": defaults.get("ram_kb"),
            "toolchain": "ARM_GCC",
        }
        sources = ["adapter defaults"]
        board = load_board(self.repo_root)
        facts.update({"board": board.get("board"), "mcu": board.get("mcu") or facts["mcu"], "led": board.get("led")})
        sources.append("board profile")
        project = _read_json(root / "project.json")
        if project:
            facts.update({k: v for k, v in project.items() if v is not None})
            sources.append("project.json")
        ioc_files = sorted(root.glob("*.ioc"))
        ioc_analysis = None
        if ioc_files:
            ioc_analysis = parse_ioc(_read_text(ioc_files[0]), ioc_files[0].name)
            for src, dst in (("mcu", "mcu"), ("family", "family"), ("board", "board"), ("clock", "clock"), ("pins", "pins"), ("peripherals", "peripherals")):
                if ioc_analysis.get(src) is not None:
                    facts[dst] = ioc_analysis[src]
            sources.append("IOC")
        return {"facts": facts, "sources": sources, "ioc": ioc_analysis}

    def mcu_info(self, root: Path) -> dict[str, Any]:
        return get_mcu_info()

    def pin_info(self, pin: str) -> dict[str, Any]:
        return get_pin_info(pin)

    def toolchain_status(self) -> dict[str, Any]:
        prepend_toolchain_path()
        gcc = shutil.which("arm-none-eabi-gcc")
        make = shutil.which("make")
        return {
            "status": "available" if gcc and make else "not_installed",
            "tools": {"arm-none-eabi-gcc": gcc, "make": make, "openocd": shutil.which("openocd")},
        }

    def build(self, root: Path) -> PlatformResult:
        try:
            result = compile_project(Path(root))
        except CompileError as exc:
            return PlatformResult.unavailable("build", self.adapter_id, str(exc))
        status = "PASS" if result.get("success") else "FAIL"
        return PlatformResult(status, "build", self.adapter_id, _without_success(result), evidence=_artifact_evidence(result))

    async def build_streaming(self, root: Path, on_line: LineCallback | None = None) -> PlatformResult:
        try:
            result = await compile_project_streaming(Path(root), on_line)
        except CompileError as exc:
            return PlatformResult.unavailable("build", self.adapter_id, str(exc))
        status = "PASS" if result.get("success") else "FAIL"
        return PlatformResult(status, "build", self.adapter_id, _without_success(result), evidence=_artifact_evidence(result))

    def clean(self, root: Path) -> PlatformResult:
        prepend_toolchain_path()
        make = shutil.which("make")
        if not make:
            return PlatformResult.unavailable("clean", self.adapter_id, "未检测到 make")
        proc = subprocess.run([make, "clean"], cwd=str(Path(root).resolve()), capture_output=True, text=True, timeout=60, check=False, shell=False)
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return PlatformResult("PASS" if proc.returncode == 0 else "FAIL", "clean", self.adapter_id, {"exit_code": proc.returncode, "output": output[-8000:]})

    def flash(self, root: Path, *, device: str | None = None) -> PlatformResult:
        chip = detect_chip_id()
        if not chip.get("available") or chip.get("family") != "STM32F1":
            return PlatformResult.unavailable("flash", self.adapter_id, "no verified STM32F1 probe evidence")
        try:
            result = flash_elf(Path(root))
        except FlashError as exc:
            return PlatformResult(status="FAIL", operation="flash", adapter_id=self.adapter_id, reason=str(exc), evidence=[str(chip.get("family"))])
        return PlatformResult("PASS" if result.get("success") else "FAIL", "flash", self.adapter_id, _without_success(result), evidence=["STM32F1 probe detected"])

    def reset(self, *, device: str | None = None) -> PlatformResult:
        chip = detect_chip_id()
        exe = shutil.which("openocd")
        if not exe or chip.get("family") != "STM32F1":
            return PlatformResult.unavailable("reset", self.adapter_id, "no verified STM32F1 probe evidence")
        proc = subprocess.run(
            [exe, "-f", ALLOWED_INTERFACE, "-f", ALLOWED_TARGET, "-c", "init; reset run; shutdown"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return PlatformResult("PASS" if proc.returncode == 0 else "FAIL", "reset", self.adapter_id, {"exit_code": proc.returncode, "output": output[-4000:]}, evidence=["STM32F1 probe detected"])

    def serial_sample(self, *, device: str | None, baud: int = 115200, seconds: float = 8.0, expect: str | None = None) -> PlatformResult:
        available = {str(item.get("device")) for item in list_ports()}
        if not device or device not in available:
            return PlatformResult.unavailable("serial", self.adapter_id, "serial device was not detected")
        try:
            result = sample_serial(device, baud, seconds, expect)
        except (ValueError, RuntimeError, OSError) as exc:
            return PlatformResult(status="FAIL", operation="serial", adapter_id=self.adapter_id, reason=str(exc))
        lines = list(result.get("lines") or [])
        return PlatformResult("PASS" if lines else "FAIL", "serial", self.adapter_id, result, reason=None if lines else "no serial output", evidence=lines[-20:])

    def generate_peripheral(self, root: Path, kind: str, args: Mapping[str, Any] | None = None) -> PlatformResult:
        result = configure_peripheral(Path(root), kind, dict(args or {}))
        return PlatformResult("PASS" if result.get("ok") else "FAIL", "generate", self.adapter_id, result, reason=result.get("reason"))

    def register_module(self, root: Path, module: str) -> PlatformResult:
        result = register_hal_module(Path(root), module)
        return PlatformResult("PASS" if result.get("ok") else "FAIL", "register-module", self.adapter_id, result)

    def validate_static(self, root: Path, task: str = "") -> PlatformResult:
        result = validate_project(Path(root), task)
        return PlatformResult("PASS" if result.get("passed") else "FAIL", "validate", self.adapter_id, result, evidence=list(result.get("kinds") or select_validators(task)))

    def validate_hardware(self, *, serial_lines: list[str] | None, expect: str | None, task: str, has_probe: bool) -> PlatformResult:
        result = hardware_status(serial_lines=serial_lines, expect=expect, task=task, has_probe=has_probe)
        status = str(result.get("status") or "UNAVAILABLE").upper()
        operation_status = status if status in {"PASS", "FAIL", "UNAVAILABLE"} else "FAIL"
        return PlatformResult(operation_status, "hardware-validation", self.adapter_id, result, reason=result.get("reason"), evidence=list(serial_lines or []))

    def hardware_run(self, root: Path, *, serial_device: str | None = None, baud: int = 115200, expect: str | None = None, task: str = "", max_hw_iterations: int = 3) -> PlatformResult:
        chip = detect_chip_id()
        if not chip.get("available") or chip.get("family") != "STM32F1":
            return PlatformResult.unavailable("hardware-run", self.adapter_id, "no verified STM32F1 probe evidence")
        result = run_pipeline(
            Path(root),
            serial_device=serial_device,
            baud=baud,
            expect=expect,
            task=task,
            max_hw_iterations=max_hw_iterations,
        )
        val_status = str((result.get("validation") or {}).get("status") or "UNAVAILABLE").upper()
        status = val_status if val_status in {"PASS", "FAIL", "UNAVAILABLE"} else "FAIL"
        return PlatformResult(status, "hardware-run", self.adapter_id, result, reason=(result.get("validation") or {}).get("reason"), evidence=["STM32F1 probe detected"])

    def auto_debug(self, root: Path, *, serial_device: str | None = None, baud: int = 115200, expect: str | None = None, task: str = "") -> PlatformResult:
        chip = detect_chip_id()
        if not chip.get("available") or chip.get("family") != "STM32F1":
            return PlatformResult.unavailable("auto-debug", self.adapter_id, "no verified STM32F1 probe evidence")
        result = stm32_auto_debug(Path(root), serial_device=serial_device, baud=baud, expect=expect)
        final = result.get("final") or {}
        status = "PASS" if (final.get("validation") or {}).get("status") == "pass" else "FAIL"
        return PlatformResult(status, "auto-debug", self.adapter_id, result, evidence=["STM32F1 probe detected"])


def _norm(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _without_success(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "success"}


def _artifact_evidence(result: Mapping[str, Any]) -> list[str]:
    return [str(item.get("name")) for item in result.get("artifacts") or [] if item.get("name")]


__all__ = ["Stm32F103Adapter"]
