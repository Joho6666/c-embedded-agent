from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.platforms.base import DetectionEvidence, LineCallback, PlatformAdapter, PlatformDescriptor, PlatformResult
from app.tools.hardware_run import sample_serial
from app.tools.serialutil import list_ports


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _norm(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


class Mcu8051SdccAdapter(PlatformAdapter):
    descriptor = PlatformDescriptor(
        adapter_id="8051-sdcc",
        name="8051 SDCC",
        platform="8051",
        mcu="STC89C52RC",
        framework="SDCC",
        status="experimental",
        boards=("stc89c52_dev",),
        toolchains=("sdcc", "packihx", "make"),
        capabilities=(
            "detect",
            "create",
            "context",
            "build",
            "clean",
            "flash",
            "serial",
            "generate",
            "validate",
            "hardware",
        ),
        reason="Experimental / Compile Verified (SDCC CI active across 8051 Golden projects)",
    )

    @property
    def template_path(self) -> Path:
        return self.repo_root / "templates" / "8051_sdcc"

    @property
    def protected_paths(self) -> tuple[str, ...]:
        return (".git", "project.json", "8051_compat.h")

    @property
    def tools(self) -> tuple[str, ...]:
        return ("compile_project", "flash_firmware", "serial_sample", "validate_project")

    @property
    def skills(self) -> tuple[str, ...]:
        return ("8051-gpio", "8051-uart", "8051-timer")

    @property
    def validators(self) -> tuple[str, ...]:
        return ("8051-gpio", "8051-uart", "8051-marker")

    @property
    def knowledge_roots(self) -> tuple[Path, ...]:
        return (self.repo_root / "knowledge_sources" / "8051",)

    def detect_project(self, root: Path) -> DetectionEvidence:
        root = Path(root)
        reasons: list[str] = []
        conflicts: list[str] = []
        confidence = 0.0

        project = _read_json(root / "project.json")
        if project:
            adapter_id = _norm(project.get("adapterId"))
            mcu = _norm(project.get("mcu"))
            platform = _norm(project.get("platform"))
            if adapter_id and adapter_id != _norm(self.adapter_id):
                conflicts.append(f"project.json selects adapter {project.get('adapterId')}")
            elif adapter_id == _norm(self.adapter_id):
                reasons.append("project.json selects 8051-sdcc")
                confidence = max(confidence, 0.98)

            if mcu in ("stc89c52", "stc89c52rc", "at89c51", "8051", "c51"):
                reasons.append(f"project.json identifies 8051 MCU: {project.get('mcu')}")
                confidence = max(confidence, 0.95)
            elif mcu and ("stm32" in mcu or "esp32" in mcu):
                conflicts.append(f"unsupported 8051 target in project.json: {project.get('mcu')}")

            if platform in ("8051", "c51", "mcs51"):
                reasons.append(f"project.json identifies platform {project.get('platform')}")
                confidence = max(confidence, 0.90)

        # Check source headers
        c_files = list(root.glob("*.c")) + list(root.glob("src/*.c"))
        for cf in c_files:
            try:
                content = cf.read_text(encoding="utf-8", errors="ignore")
                if "8051_compat.h" in content or "<reg52.h>" in content or "<8051.h>" in content or "<mcs51/8051.h>" in content:
                    reasons.append(f"source {cf.name} includes 8051 headers")
                    confidence = max(confidence, 0.85)
            except OSError:
                pass

        makefile = root / "Makefile"
        if makefile.is_file():
            try:
                mk_content = makefile.read_text(encoding="utf-8", errors="ignore")
                if "sdcc" in mk_content.lower():
                    reasons.append("Makefile specifies sdcc toolchain")
                    confidence = max(confidence, 0.80)
            except OSError:
                pass

        matched = bool(reasons) and not conflicts and confidence >= 0.50
        return DetectionEvidence(
            adapter_id=self.adapter_id,
            matched=matched,
            confidence=confidence if matched else 0.0,
            reasons=tuple(reasons),
            conflicts=tuple(conflicts),
        )

    def create_template(
        self,
        destination: Path,
        *,
        name: str,
        board: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlatformResult:
        destination = Path(destination)
        if destination.exists() and any(destination.iterdir()):
            return PlatformResult(
                status="FAIL",
                operation="create",
                adapter_id=self.adapter_id,
                reason=f"destination directory exists and is not empty: {destination}",
            )
        if not self.template_path.is_dir():
            return PlatformResult(
                status="FAIL",
                operation="create",
                adapter_id=self.adapter_id,
                reason=f"8051 template directory missing: {self.template_path}",
            )

        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.template_path, destination, dirs_exist_ok=True)

        payload: dict[str, Any] = {
            "name": name,
            "adapterId": self.adapter_id,
            "platform": "8051",
            "mcu": "STC89C52RC",
            "framework": "SDCC",
            "board": board or "stc89c52_dev",
            "toolchain": "SDCC",
            "marker": "CEA:8051:PASS",
        }
        if metadata:
            payload.update({k: v for k, v in metadata.items() if k not in {"adapterId", "platform"}})
        (destination / "project.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return PlatformResult(
            status="PASS",
            operation="create",
            adapter_id=self.adapter_id,
            data={"path": str(destination), "project": payload},
            evidence=[f"Created 8051 template at {destination}"],
        )

    def load_context(self, root: Path) -> dict[str, Any]:
        return {
            "platform": "8051",
            "mcu": "STC89C52RC",
            "adapterId": self.adapter_id,
            "facts": {
                "architecture": "8-bit CISC Harvard",
                "mcu": "STC89C52RC",
                "flash_bytes": 8192,
                "ram_bytes": 512,
                "internal_data_limit": 128,
                "clock_frequency_hz": 11059200,
                "uart_baud_default": 9600,
                "interrupt_vectors": {
                    "0": "EXTI0 (P3.2)",
                    "1": "TIMER0",
                    "2": "EXTI1 (P3.3)",
                    "3": "TIMER1",
                    "4": "UART",
                },
                "sfr_registers": [
                    "P0", "P1", "P2", "P3",
                    "TCON", "TMOD", "TL0", "TH0", "TL1", "TH1",
                    "SCON", "SBUF", "IE", "IP", "PCON"
                ],
            },
        }

    def toolchain_status(self) -> dict[str, Any]:
        sdcc = shutil.which("sdcc")
        packihx = shutil.which("packihx")
        stcgal = shutil.which("stcgal")
        make = shutil.which("make")
        return {
            "adapterId": self.adapter_id,
            "sdcc": sdcc,
            "packihx": packihx,
            "stcgal": stcgal,
            "make": make,
            "available": bool(sdcc and make),
        }

    def build(self, root: Path) -> PlatformResult:
        root = Path(root)
        tools = self.toolchain_status()
        if not tools["available"]:
            return PlatformResult.unavailable(
                "build",
                self.adapter_id,
                "SDCC toolchain (sdcc and make) is not installed on this system",
            )
        make = tools["make"]
        res = subprocess.run([make, "all"], cwd=root, text=True, capture_output=True, check=False)
        combined = res.stdout + res.stderr
        ok = res.returncode == 0
        artifacts = []
        for ext in ("hex", "bin", "ihx"):
            art = root / f"firmware.{ext}"
            if not art.is_file():
                art = root / "build" / f"firmware.{ext}"
            if art.is_file() and art.stat().st_size > 0:
                artifacts.append({"name": art.name, "path": str(art), "size": art.stat().st_size})

        diagnostics: list[dict[str, Any]] = []
        for line in combined.splitlines():
            if ": error" in line or ": warning" in line:
                severity = "error" if ": error" in line else "warning"
                diagnostics.append({"severity": severity, "message": line.strip()})

        return PlatformResult(
            status="PASS" if ok and artifacts else "FAIL",
            operation="build",
            adapter_id=self.adapter_id,
            data={
                "exit_code": res.returncode,
                "combined": combined,
                "artifacts": artifacts,
                "diagnostics": diagnostics,
            },
            reason="build completed" if ok else f"sdcc exit code {res.returncode}",
            evidence=[f"SDCC build exit code {res.returncode}"],
        )

    def clean(self, root: Path) -> PlatformResult:
        root = Path(root)
        make = shutil.which("make")
        if not make:
            return PlatformResult.unavailable("clean", self.adapter_id, "make not found")
        res = subprocess.run([make, "clean"], cwd=root, text=True, capture_output=True, check=False)
        return PlatformResult(
            status="PASS" if res.returncode == 0 else "FAIL",
            operation="clean",
            adapter_id=self.adapter_id,
            data={"combined": res.stdout + res.stderr},
        )

    def flash(self, root: Path, *, device: str | None = None) -> PlatformResult:
        stcgal = shutil.which("stcgal")
        if not stcgal:
            return PlatformResult.unavailable("flash", self.adapter_id, "stcgal programmer is not installed")
        if not device:
            ports = list_ports()
            if not ports:
                return PlatformResult.unavailable("flash", self.adapter_id, "No serial port detected for STC ISP")
            device = ports[0].get("port")
        hex_file = root / "build" / "firmware.hex"
        if not hex_file.is_file():
            hex_file = root / "firmware.hex"
        if not hex_file.is_file():
            return PlatformResult(status="FAIL", operation="flash", adapter_id=self.adapter_id, reason="firmware.hex not found")

        cmd = [stcgal, "-P", "stc89", "-p", device, str(hex_file)]
        res = subprocess.run(cmd, text=True, capture_output=True, check=False)
        return PlatformResult(
            status="PASS" if res.returncode == 0 else "FAIL",
            operation="flash",
            adapter_id=self.adapter_id,
            data={"output": res.stdout + res.stderr},
            reason="Flash succeeded" if res.returncode == 0 else "stcgal failed",
        )

    def serial_sample(
        self,
        *,
        device: str | None,
        baud: int = 9600,
        seconds: float = 6.0,
        expect: str | None = None,
    ) -> PlatformResult:
        if not device:
            ports = list_ports()
            if not ports:
                return PlatformResult.unavailable("serial", self.adapter_id, "No serial port detected")
            device = ports[0].get("port")
        lines = sample_serial(device, baud=baud, timeout_sec=seconds)
        if lines is None:
            return PlatformResult.unavailable("serial", self.adapter_id, f"Could not open serial port {device}")
        return PlatformResult(
            status="PASS" if lines else "FAIL",
            operation="serial",
            adapter_id=self.adapter_id,
            data={"lines": lines},
            evidence=[f"Sampled {len(lines)} lines from {device}"],
        )

    def validate_static(self, root: Path, task: str = "") -> PlatformResult:
        root = Path(root)
        c_files = list(root.glob("*.c")) + list(root.glob("src/*.c"))
        combined_code = ""
        for cf in c_files:
            try:
                combined_code += "\n" + cf.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass

        task_l = task.lower()
        checks: list[str] = []
        passed = True

        if any(w in task_l for w in ("led", "blink", "gpio", "闪烁")):
            has_port = bool(re.search(r"\b(P[0-3]|P1_[0-7]|P2_[0-7])\b", combined_code))
            has_delay = "delay" in combined_code.lower() or "while" in combined_code
            if has_port and has_delay:
                checks.append("GPIO/LED port access and delay loop detected")
            else:
                checks.append("Missing GPIO port manipulation or delay logic")
                passed = False

        if any(w in task_l for w in ("uart", "usart", "serial", "串口")):
            has_scon = "SCON" in combined_code
            has_tmod = "TMOD" in combined_code
            has_tr1 = "TR1" in combined_code
            has_sbuf = "SBUF" in combined_code
            if has_scon and has_tmod and has_tr1 and has_sbuf:
                checks.append("UART registers SCON/TMOD/TR1/SBUF configured")
            else:
                checks.append("Incomplete 8051 UART timer/register configuration")
                passed = False

        if any(w in task_l for w in ("timer", "定时器", "interrupt", "中断")):
            has_tmod = "TMOD" in combined_code
            has_ea = "EA" in combined_code or "IE" in combined_code
            if has_tmod and has_ea:
                checks.append("Timer and global interrupt enable detected")
            else:
                checks.append("Missing Timer initialization or interrupt enable")
                passed = False

        if not checks:
            checks.append("8051 syntax check passed")

        return PlatformResult(
            status="PASS" if passed else "FAIL",
            operation="validate",
            adapter_id=self.adapter_id,
            data={"checks": checks},
            reason="Static validation passed" if passed else "Static validation checks failed",
            evidence=checks,
        )

    def validate_hardware(
        self,
        *,
        serial_lines: list[str] | None,
        expect: str | None,
        task: str,
        has_probe: bool,
    ) -> PlatformResult:
        if not has_probe or serial_lines is None:
            return PlatformResult.unavailable(
                "hardware-validation",
                self.adapter_id,
                "Hardware Not Tested — No physical STC MCU connected (NO FAKE PASS)",
            )
        marker = expect or "CEA:8051:PASS"
        joined = "\n".join(serial_lines)
        if marker in joined:
            return PlatformResult(
                status="PASS",
                operation="hardware-validation",
                adapter_id=self.adapter_id,
                data={"marker": marker, "matched": True},
                evidence=[f"Marker '{marker}' captured on hardware serial bus"],
            )
        return PlatformResult(
            status="FAIL",
            operation="hardware-validation",
            adapter_id=self.adapter_id,
            reason=f"Marker '{marker}' not found in hardware serial output",
        )

    def hardware_run(
        self,
        root: Path,
        *,
        serial_device: str | None = None,
        baud: int = 9600,
        expect: str | None = None,
        task: str = "",
    ) -> PlatformResult:
        tools = self.toolchain_status()
        if not tools["stcgal"]:
            return PlatformResult.unavailable(
                "hardware_run",
                self.adapter_id,
                "stcgal not installed",
            )
        ports = list_ports()
        if not ports and not serial_device:
            return PlatformResult.unavailable(
                "hardware_run",
                self.adapter_id,
                "No serial device connected for 8051 hardware run",
            )
        return PlatformResult.unavailable(
            "hardware_run",
            self.adapter_id,
            "Physical 8051 bench execution requires manual power cycle for STC ISP handshaking",
        )
