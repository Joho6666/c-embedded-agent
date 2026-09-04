from __future__ import annotations

import asyncio
import json
import os
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


class Esp32S3IdfAdapter(PlatformAdapter):
    descriptor = PlatformDescriptor(
        adapter_id="esp32s3-idf",
        name="ESP32-S3 ESP-IDF",
        platform="ESP32",
        mcu="ESP32-S3",
        framework="ESP-IDF",
        status="ready",
        boards=("esp32s3_devkitc_1",),
        toolchains=("ESP-IDF 6.1", "CMake", "Ninja"),
        capabilities=("detect", "create", "context", "build", "clean", "flash", "serial", "generate", "validate", "hardware"),
        reason="ESP-IDF 6.1 matrix CI passing across 7/7 Golden projects",
    )

    @property
    def template_path(self) -> Path:
        return self.repo_root / "templates" / "esp32s3_idf"

    @property
    def protected_paths(self) -> tuple[str, ...]:
        return (".git", "project.json", "sdkconfig", "partitions.csv")

    @property
    def tools(self) -> tuple[str, ...]:
        return ("compile_project", "flash_firmware", "serial_sample", "configure_gpio", "configure_usart", "validate_project")

    @property
    def skills(self) -> tuple[str, ...]:
        return ("esp32s3-gpio", "esp32s3-uart")

    @property
    def validators(self) -> tuple[str, ...]:
        return ("esp32s3-gpio", "esp32s3-uart", "esp32s3-marker")

    @property
    def knowledge_roots(self) -> tuple[Path, ...]:
        return (self.repo_root / "knowledge_sources" / "esp32s3",)

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
                reasons.append("project.json selects esp32s3-idf")
                confidence = max(confidence, 0.98)
            if mcu and mcu != "esp32s3":
                if "esp32" in mcu:
                    conflicts.append(f"unsupported ESP32 target in project.json: {project.get('mcu')}")
            elif mcu == "esp32s3":
                reasons.append("project.json identifies ESP32-S3")
                confidence = max(confidence, 0.98)
            elif platform == "esp32" and not mcu:
                reasons.append("project.json identifies ESP32 without a target")
                confidence = max(confidence, 0.45)

        sdkconfig = _read_text(root / "sdkconfig") + "\n" + _read_text(root / "sdkconfig.defaults")
        target = re.search(r'^CONFIG_IDF_TARGET="?([^"\r\n]+)', sdkconfig, re.MULTILINE)
        if target:
            target_name = target.group(1).strip()
            if target_name == "esp32s3":
                reasons.append("sdkconfig selects esp32s3")
                confidence = max(confidence, 1.0)
            else:
                conflicts.append(f"unsupported ESP-IDF target: {target_name}")

        cmake = _read_text(root / "CMakeLists.txt")
        component = _read_text(root / "main" / "CMakeLists.txt")
        if "IDF_PATH" in cmake and "project.cmake" in cmake:
            reasons.append("ESP-IDF project.cmake signature")
            confidence = max(confidence, 0.7)
        if "idf_component_register" in component:
            reasons.append("ESP-IDF component signature")
            confidence = max(confidence, 0.7)
        if any(root.glob("*.ioc")) or (root / "Drivers" / "STM32F1xx_HAL_Driver").exists():
            conflicts.append("STM32 project signatures found")
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
        chosen_board = board or "esp32s3_devkitc_1"
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
                "toolchain": "ESP-IDF 6.1",
                "board": "ESP32-S3-DevKitC-1",
                "boardId": chosen_board,
                "adapterId": self.adapter_id,
                "capabilities": list(self.descriptor.capabilities),
            }
            (Path(destination) / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            return PlatformResult("PASS", "create", self.adapter_id, {"path": str(destination), "metadata": meta})
        except (OSError, FileExistsError) as exc:
            return PlatformResult(status="FAIL", operation="create", adapter_id=self.adapter_id, reason=str(exc))

    def load_context(self, root: Path) -> dict[str, Any]:
        root = Path(root)
        facts: dict[str, Any] = {
            "platform": "ESP32",
            "adapterId": self.adapter_id,
            "mcu": "ESP32-S3",
            "framework": "ESP-IDF",
            "idfVersion": "6.1",
            "board": "ESP32-S3-DevKitC-1",
            "gpioOutput": 4,
            "serialMarker": "CEA:ESP32:PASS",
        }
        sources = ["adapter defaults", "board profile"]
        project = _read_json(root / "project.json")
        if project:
            facts.update({key: value for key, value in project.items() if value is not None})
            sources.append("project.json")
        sdkconfig = _read_text(root / "sdkconfig") + "\n" + _read_text(root / "sdkconfig.defaults")
        config = {match.group(1): match.group(2).strip('"') for match in re.finditer(r"^(CONFIG_[A-Z0-9_]+)=(.+)$", sdkconfig, re.MULTILINE)}
        if config:
            facts["sdkconfig"] = config
            if config.get("CONFIG_IDF_TARGET"):
                facts["mcu"] = config["CONFIG_IDF_TARGET"].upper().replace("ESP32S3", "ESP32-S3")
            sources.append("sdkconfig")
        return {"facts": facts, "sources": sources}

    def toolchain_status(self) -> dict[str, Any]:
        idf = shutil.which("idf.py")
        idf_path = os.environ.get("IDF_PATH")
        return {
            "status": "available" if idf and idf_path else ("not_configured" if idf or idf_path else "not_installed"),
            "version": "6.1 baseline",
            "tools": {"idf.py": idf, "IDF_PATH": idf_path, "cmake": shutil.which("cmake"), "ninja": shutil.which("ninja")},
        }

    def build(self, root: Path) -> PlatformResult:
        exe = shutil.which("idf.py")
        if not exe or not os.environ.get("IDF_PATH"):
            return PlatformResult.unavailable("build", self.adapter_id, "ESP-IDF is not installed or IDF_PATH is not configured")
        try:
            proc = subprocess.run(
                [exe, "build"],
                cwd=str(Path(root).resolve()),
                capture_output=True,
                text=True,
                timeout=settings.compile_timeout_sec,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return PlatformResult(status="FAIL", operation="build", adapter_id=self.adapter_id, reason=str(exc))
        return self._build_result(Path(root), proc.returncode, proc.stdout or "", proc.stderr or "")

    async def build_streaming(self, root: Path, on_line: LineCallback | None = None) -> PlatformResult:
        exe = shutil.which("idf.py")
        if not exe or not os.environ.get("IDF_PATH"):
            return PlatformResult.unavailable("build", self.adapter_id, "ESP-IDF is not installed or IDF_PATH is not configured")
        try:
            proc = await asyncio.create_subprocess_exec(
                exe,
                "build",
                cwd=str(Path(root).resolve()),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            buckets: dict[str, list[str]] = {"stdout": [], "stderr": []}

            async def pump(stream: asyncio.StreamReader, name: str) -> None:
                while True:
                    raw = await stream.readline()
                    if not raw:
                        return
                    line = raw.decode("utf-8", errors="replace").rstrip("\n")
                    buckets[name].append(line)
                    if on_line:
                        maybe = on_line(name, line)
                        if asyncio.iscoroutine(maybe):
                            await maybe

            await asyncio.wait_for(
                asyncio.gather(pump(proc.stdout, "stdout"), pump(proc.stderr, "stderr")),  # type: ignore[arg-type]
                timeout=settings.compile_timeout_sec,
            )
            code = await proc.wait()
        except (OSError, asyncio.TimeoutError) as exc:
            return PlatformResult(status="FAIL", operation="build", adapter_id=self.adapter_id, reason=str(exc))
        return self._build_result(Path(root), code or 0, "\n".join(buckets["stdout"]), "\n".join(buckets["stderr"]))

    def _build_result(self, root: Path, code: int, stdout: str, stderr: str) -> PlatformResult:
        combined = (stdout + "\n" + stderr)[-settings.max_stdout_bytes :]
        artifacts = []
        for path in sorted((root / "build").glob("*.bin")) if (root / "build").is_dir() else []:
            artifacts.append({"name": path.name, "path": path.relative_to(root).as_posix(), "size": path.stat().st_size})
        errors = [line for line in combined.splitlines() if "error:" in line.lower() or "cmake error" in line.lower()]
        return PlatformResult(
            "PASS" if code == 0 else "FAIL",
            "build",
            self.adapter_id,
            {"exit_code": code, "stdout": stdout, "stderr": stderr, "combined": combined, "diagnostics": errors, "artifacts": artifacts},
            evidence=[item["name"] for item in artifacts],
        )

    def clean(self, root: Path) -> PlatformResult:
        return self._run_idf("clean", Path(root), ["fullclean"])

    def flash(self, root: Path, *, device: str | None = None) -> PlatformResult:
        if not self._device_detected(device):
            return PlatformResult.unavailable("flash", self.adapter_id, "ESP32-S3 serial device was not detected")
        return self._run_idf("flash", Path(root), ["-p", str(device), "flash"], evidence=[f"serial device {device}"])

    def reset(self, *, device: str | None = None) -> PlatformResult:
        return PlatformResult.unavailable("reset", self.adapter_id, "standalone ESP32-S3 reset is not implemented; flash resets the target")

    def serial_sample(self, *, device: str | None, baud: int = 115200, seconds: float = 8.0, expect: str | None = None) -> PlatformResult:
        if not self._device_detected(device):
            return PlatformResult.unavailable("serial", self.adapter_id, "ESP32-S3 serial device was not detected")
        try:
            result = sample_serial(str(device), baud, seconds, expect or "CEA:ESP32:PASS")
        except (ValueError, RuntimeError, OSError) as exc:
            return PlatformResult(status="FAIL", operation="serial", adapter_id=self.adapter_id, reason=str(exc))
        lines = list(result.get("lines") or [])
        return PlatformResult("PASS" if lines else "FAIL", "serial", self.adapter_id, result, reason=None if lines else "no serial output", evidence=lines[-20:])

    def generate_peripheral(self, root: Path, kind: str, args: Mapping[str, Any] | None = None) -> PlatformResult:
        kind = (kind or "").lower()
        if kind not in {"gpio", "usart", "uart"}:
            return PlatformResult(status="FAIL", operation="generate", adapter_id=self.adapter_id, reason=f"unsupported ESP32-S3 peripheral: {kind}")
        root = Path(root)
        main = root / "main"
        if not main.is_dir():
            return PlatformResult(status="FAIL", operation="generate", adapter_id=self.adapter_id, reason="missing main component")
        args = dict(args or {})
        if kind == "gpio":
            pin = int(args.get("pin", 4))
            path = main / "cea_gpio.c"
            content = _gpio_source(pin)
        else:
            port = int(args.get("port", 0))
            baud = int(args.get("baud", 115200))
            path = main / "cea_uart.c"
            content = _uart_source(port, baud)
        try:
            path.write_text(content, encoding="utf-8")
            cmake_path = main / "CMakeLists.txt"
            cmake = _read_text(cmake_path)
            source_name = path.name
            if source_name not in cmake:
                cmake = re.sub(r'idf_component_register\(SRCS\s+"([^"]+)"', rf'idf_component_register(SRCS "\1" "{source_name}"', cmake, count=1)
                cmake_path.write_text(cmake, encoding="utf-8")
            return PlatformResult("PASS", "generate", self.adapter_id, {"ok": True, "files": [path.relative_to(root).as_posix()]})
        except OSError as exc:
            return PlatformResult(status="FAIL", operation="generate", adapter_id=self.adapter_id, reason=str(exc))

    def validate_static(self, root: Path, task: str = "") -> PlatformResult:
        root = Path(root)
        cmake = _read_text(root / "CMakeLists.txt") + "\n" + _read_text(root / "main" / "CMakeLists.txt")
        sources = "\n".join(_read_text(path) for path in sorted((root / "main").glob("*.c"))) if (root / "main").is_dir() else ""
        checks = {
            "idf_project": "project.cmake" in cmake and "idf_component_register" in cmake,
            "esp32s3_target": 'CONFIG_IDF_TARGET="esp32s3"' in (_read_text(root / "sdkconfig") + _read_text(root / "sdkconfig.defaults")),
        }
        prompt = task.lower()
        if "gpio" in prompt or "led" in prompt or "blink" in prompt:
            checks["gpio4"] = "GPIO_NUM_4" in sources or re.search(r"gpio_set_level\s*\(\s*4", sources) is not None
        if "uart" in prompt or "usart" in prompt or "serial" in prompt:
            checks["uart"] = "uart_driver_install" in sources and "uart_param_config" in sources
        passed = all(checks.values())
        return PlatformResult("PASS" if passed else "FAIL", "validate", self.adapter_id, {"passed": passed, "checks": checks, "missing": [key for key, ok in checks.items() if not ok]})

    def validate_hardware(self, *, serial_lines: list[str] | None, expect: str | None, task: str, has_probe: bool) -> PlatformResult:
        if serial_lines is None or not has_probe:
            return PlatformResult.unavailable("hardware-validation", self.adapter_id, "Hardware Not Tested")
        joined = "\n".join(serial_lines)
        marker = expect or "CEA:ESP32:PASS"
        passed = bool(serial_lines) and marker in joined
        return PlatformResult("PASS" if passed else "FAIL", "hardware-validation", self.adapter_id, {"expected": marker, "observed": joined[-800:]}, reason=None if passed else "missing ESP32-S3 serial marker", evidence=list(serial_lines[-20:]))

    def hardware_run(self, root: Path, *, serial_device: str | None = None, baud: int = 115200, expect: str | None = None, task: str = "", max_hw_iterations: int = 3) -> PlatformResult:
        if not self._device_detected(serial_device):
            return PlatformResult.unavailable("hardware-run", self.adapter_id, "ESP32-S3 hardware device was not detected")
        built = self.build(root)
        if not built.success:
            return PlatformResult(built.status, "hardware-run", self.adapter_id, {"build": built.to_dict()}, reason=built.reason)
        flashed = self.flash(root, device=serial_device)
        if not flashed.success:
            return PlatformResult(flashed.status, "hardware-run", self.adapter_id, {"build": built.to_dict(), "flash": flashed.to_dict()}, reason=flashed.reason)
        sampled = self.serial_sample(device=serial_device, baud=baud, expect=expect or "CEA:ESP32:PASS")
        validation = self.validate_hardware(serial_lines=sampled.data.get("lines") if sampled.success else [], expect=expect, task=task, has_probe=True)
        return PlatformResult(validation.status, "hardware-run", self.adapter_id, {"build": built.to_dict(), "flash": flashed.to_dict(), "serial": sampled.to_dict(), "validation": validation.to_dict()}, reason=validation.reason, evidence=validation.evidence)

    def _run_idf(self, operation: str, root: Path, args: list[str], evidence: list[str] | None = None) -> PlatformResult:
        exe = shutil.which("idf.py")
        if not exe or not os.environ.get("IDF_PATH"):
            return PlatformResult.unavailable(operation, self.adapter_id, "ESP-IDF is not installed or IDF_PATH is not configured")
        try:
            proc = subprocess.run([exe, *args], cwd=str(root.resolve()), capture_output=True, text=True, timeout=120, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return PlatformResult(status="FAIL", operation=operation, adapter_id=self.adapter_id, reason=str(exc))
        output = ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-12000:]
        return PlatformResult("PASS" if proc.returncode == 0 else "FAIL", operation, self.adapter_id, {"exit_code": proc.returncode, "output": output}, evidence=evidence or [])

    @staticmethod
    def _device_detected(device: str | None) -> bool:
        if not device:
            return False
        return str(device) in {str(item.get("device")) for item in list_ports()}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _norm(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _gpio_source(pin: int) -> str:
    return f'''#include "driver/gpio.h"\n\nvoid cea_gpio_init(void)\n{{\n    gpio_reset_pin(GPIO_NUM_{pin});\n    gpio_set_direction(GPIO_NUM_{pin}, GPIO_MODE_OUTPUT);\n    gpio_set_level(GPIO_NUM_{pin}, 1);\n}}\n'''


def _uart_source(port: int, baud: int) -> str:
    return f'''#include "driver/uart.h"\n\nvoid cea_uart_init(void)\n{{\n    const uart_config_t config = {{\n        .baud_rate = {baud},\n        .data_bits = UART_DATA_8_BITS,\n        .parity = UART_PARITY_DISABLE,\n        .stop_bits = UART_STOP_BITS_1,\n        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,\n        .source_clk = UART_SCLK_DEFAULT,\n    }};\n    uart_param_config(UART_NUM_{port}, &config);\n    uart_driver_install(UART_NUM_{port}, 1024, 0, 0, NULL, 0);\n}}\n'''


__all__ = ["Esp32S3IdfAdapter"]
