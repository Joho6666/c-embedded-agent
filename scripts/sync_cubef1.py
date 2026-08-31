#!/usr/bin/env python3
"""Vendor a minimal official STM32CubeF1 subset into templates/stm32f103_hal_official/Drivers."""
from __future__ import annotations

import ipaddress
import socket
import ssl
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "templates" / "stm32f103_hal_official"

CMSIS_TAG = "v1.8.6"
DEVICE_TAG = "v4.3.5"
HAL_TAG = "v1.1.9"

CMSIS_BASE = f"https://raw.githubusercontent.com/STMicroelectronics/STM32CubeF1/{CMSIS_TAG}"
DEVICE_BASE = f"https://raw.githubusercontent.com/STMicroelectronics/cmsis-device-f1/{DEVICE_TAG}"
HAL_BASE = f"https://raw.githubusercontent.com/STMicroelectronics/stm32f1xx-hal-driver/{HAL_TAG}"

ALLOWED_HOSTS = {"raw.githubusercontent.com"}

CMSIS_FILES = [
    "Drivers/CMSIS/Include/cmsis_compiler.h",
    "Drivers/CMSIS/Include/cmsis_gcc.h",
    "Drivers/CMSIS/Include/cmsis_version.h",
    "Drivers/CMSIS/Include/core_cm3.h",
    "Drivers/CMSIS/Include/mpu_armv7.h",
]

DEVICE_FILES = [
    ("Include/stm32f1xx.h", "Drivers/CMSIS/Device/ST/STM32F1xx/Include/stm32f1xx.h"),
    ("Include/stm32f103xb.h", "Drivers/CMSIS/Device/ST/STM32F1xx/Include/stm32f103xb.h"),
    ("Include/system_stm32f1xx.h", "Drivers/CMSIS/Device/ST/STM32F1xx/Include/system_stm32f1xx.h"),
    ("Source/Templates/system_stm32f1xx.c", "Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/system_stm32f1xx.c"),
    ("Source/Templates/gcc/startup_stm32f103xb.s", "Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/gcc/startup_stm32f103xb.s"),
]

HAL_NAMES = [
    "stm32f1xx_hal",
    "stm32f1xx_hal_def",
    "stm32f1xx_hal_gpio",
    "stm32f1xx_hal_gpio_ex",
    "stm32f1xx_hal_rcc",
    "stm32f1xx_hal_rcc_ex",
    "stm32f1xx_hal_cortex",
    "stm32f1xx_hal_dma",
    "stm32f1xx_hal_dma_ex",
    "stm32f1xx_hal_flash",
    "stm32f1xx_hal_flash_ex",
    "stm32f1xx_hal_pwr",
    "stm32f1xx_hal_exti",
    "stm32f1xx_hal_uart",
    "stm32f1xx_hal_usart",
    "stm32f1xx_hal_tim",
    "stm32f1xx_hal_tim_ex",
    "stm32f1xx_hal_adc",
    "stm32f1xx_hal_adc_ex",
    "stm32f1xx_hal_i2c",
    "stm32f1xx_hal_spi",
]


def assert_public_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError("only https allowed")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise RuntimeError(f"unexpected host: {host}")
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            raise RuntimeError(f"blocked ip {ip}")


def fetch(url: str) -> bytes:
    assert_public_https(url)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "c-embedded-agent-cubef1-sync"})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:  # noqa: S310
        if resp.status != 200:
            raise RuntimeError(f"{resp.status} {url}")
        return resp.read()


def write_rel(rel: str, data: bytes) -> None:
    dest = DEST / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"ok {rel} ({len(data)} bytes)")


def main() -> int:
    failed: list[str] = []

    for rel in CMSIS_FILES:
        try:
            write_rel(rel, fetch(f"{CMSIS_BASE}/{rel}"))
        except Exception as e:  # noqa: BLE001
            failed.append(f"{rel}: {e}")
            print(f"FAIL {rel}: {e}", file=sys.stderr)

    for src, dest in DEVICE_FILES:
        try:
            write_rel(dest, fetch(f"{DEVICE_BASE}/{src}"))
        except Exception as e:  # noqa: BLE001
            failed.append(f"{dest}: {e}")
            print(f"FAIL {dest}: {e}", file=sys.stderr)

    extra_hal = [
        ("Inc/Legacy/stm32_hal_legacy.h", "Drivers/STM32F1xx_HAL_Driver/Inc/Legacy/stm32_hal_legacy.h"),
        ("Inc/stm32f1xx_hal_conf_template.h", "Drivers/STM32F1xx_HAL_Driver/Inc/stm32f1xx_hal_conf_template.h"),
    ]
    for src, dest in extra_hal:
        try:
            write_rel(dest, fetch(f"{HAL_BASE}/{src}"))
        except Exception as e:  # noqa: BLE001
            failed.append(f"{dest}: {e}")
            print(f"FAIL {dest}: {e}", file=sys.stderr)

    header_only = {"stm32f1xx_hal_def", "stm32f1xx_hal_gpio_ex", "stm32f1xx_hal_dma_ex"}
    for name in HAL_NAMES:
        header = f"Inc/{name}.h"
        dest_h = f"Drivers/STM32F1xx_HAL_Driver/Inc/{name}.h"
        try:
            write_rel(dest_h, fetch(f"{HAL_BASE}/{header}"))
        except Exception as e:  # noqa: BLE001
            failed.append(f"{dest_h}: {e}")
            print(f"FAIL {dest_h}: {e}", file=sys.stderr)
        if name in header_only:
            continue
        src = f"Src/{name}.c"
        dest_c = f"Drivers/STM32F1xx_HAL_Driver/Src/{name}.c"
        try:
            write_rel(dest_c, fetch(f"{HAL_BASE}/{src}"))
        except Exception as e:  # noqa: BLE001
            failed.append(f"{dest_c}: {e}")
            print(f"FAIL {dest_c}: {e}", file=sys.stderr)

    startup_src = DEST / "Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/gcc/startup_stm32f103xb.s"
    system_src = DEST / "Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/system_stm32f1xx.c"
    if startup_src.is_file():
        (DEST / "startup_stm32f103xb.s").write_bytes(startup_src.read_bytes())
    if system_src.is_file():
        (DEST / "Core/Src").mkdir(parents=True, exist_ok=True)
        (DEST / "Core/Src/system_stm32f1xx.c").write_bytes(system_src.read_bytes())

    (DEST / "THIRD_PARTY.md").write_text(
        "# Third-party: STM32CubeF1 subset\n\n"
        f"- CMSIS-Core headers: STMicroelectronics/STM32CubeF1 {CMSIS_TAG}\n"
        f"- CMSIS Device F1: STMicroelectronics/cmsis-device-f1 {DEVICE_TAG}\n"
        f"- HAL Driver: STMicroelectronics/stm32f1xx-hal-driver {HAL_TAG}\n\n"
        "Licenses: BSD-3-Clause (ST HAL / CMSIS Device). ARM CMSIS-Core is Apache-2.0.\n"
        "Synced by scripts/sync_cubef1.py — subset only, not the full Cube package.\n",
        encoding="utf-8",
    )
    if failed:
        print("FAILED FILES:", file=sys.stderr)
        for item in failed:
            print(" ", item, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
