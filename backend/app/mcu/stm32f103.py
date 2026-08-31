from __future__ import annotations

from pathlib import Path
from typing import Any

MCU: dict[str, Any] = {
    "name": "STM32F103C8T6",
    "family": "STM32F1",
    "core": "Cortex-M3",
    "clock_mhz": 72,
    "flash_kb": 64,
    "ram_kb": 20,
    "debug": "SWD",
    "peripherals": [
        "USART1",
        "USART2",
        "USART3",
        "ADC1",
        "ADC2",
        "TIM1",
        "TIM2",
        "TIM3",
        "TIM4",
        "I2C1",
        "I2C2",
        "SPI1",
        "SPI2",
        "CAN",
        "USB",
    ],
}

# Common AF / GPIO functions for STM32F103 medium-density (RM0008).
PINS: dict[str, list[str]] = {
    "PA0": ["GPIO", "ADC1_IN0", "ADC2_IN0", "TIM2_CH1", "WKUP"],
    "PA1": ["GPIO", "ADC1_IN1", "ADC2_IN1", "TIM2_CH2"],
    "PA2": ["GPIO", "ADC1_IN2", "USART2_TX", "TIM2_CH3"],
    "PA3": ["GPIO", "ADC1_IN3", "USART2_RX", "TIM2_CH4"],
    "PA4": ["GPIO", "ADC1_IN4", "SPI1_NSS"],
    "PA5": ["GPIO", "ADC1_IN5", "SPI1_SCK"],
    "PA6": ["GPIO", "ADC1_IN6", "SPI1_MISO", "TIM3_CH1"],
    "PA7": ["GPIO", "ADC1_IN7", "SPI1_MOSI", "TIM3_CH2"],
    "PA8": ["GPIO", "TIM1_CH1", "USART1_CK"],
    "PA9": ["GPIO", "USART1_TX", "TIM1_CH2"],
    "PA10": ["GPIO", "USART1_RX", "TIM1_CH3"],
    "PA11": ["GPIO", "USART1_CTS", "USB_DM", "TIM1_CH4", "CAN_RX"],
    "PA12": ["GPIO", "USART1_RTS", "USB_DP", "CAN_TX"],
    "PA13": ["SWDIO", "GPIO"],
    "PA14": ["SWCLK", "GPIO"],
    "PA15": ["GPIO", "SPI1_NSS", "TIM2_CH1"],
    "PB0": ["GPIO", "ADC1_IN8", "TIM3_CH3"],
    "PB1": ["GPIO", "ADC1_IN9", "TIM3_CH4"],
    "PB3": ["GPIO", "SPI1_SCK", "TIM2_CH2"],
    "PB4": ["GPIO", "SPI1_MISO", "TIM3_CH1"],
    "PB5": ["GPIO", "SPI1_MOSI", "TIM3_CH2"],
    "PB6": ["GPIO", "I2C1_SCL", "TIM4_CH1", "USART1_TX"],
    "PB7": ["GPIO", "I2C1_SDA", "TIM4_CH2", "USART1_RX"],
    "PB8": ["GPIO", "I2C1_SCL", "TIM4_CH3", "CAN_RX"],
    "PB9": ["GPIO", "I2C1_SDA", "TIM4_CH4", "CAN_TX"],
    "PB10": ["GPIO", "I2C2_SCL", "USART3_TX", "TIM2_CH3"],
    "PB11": ["GPIO", "I2C2_SDA", "USART3_RX", "TIM2_CH4"],
    "PB12": ["GPIO", "SPI2_NSS", "I2C2_SMBA"],
    "PB13": ["GPIO", "SPI2_SCK", "USART3_CTS"],
    "PB14": ["GPIO", "SPI2_MISO", "USART3_RTS"],
    "PB15": ["GPIO", "SPI2_MOSI"],
    "PC13": ["GPIO", "TAMPER"],
    "PC14": ["OSC32_IN"],
    "PC15": ["OSC32_OUT"],
    "PD0": ["OSC_IN"],
    "PD1": ["OSC_OUT"],
}


def get_mcu_info() -> dict[str, Any]:
    return dict(MCU)


def get_pin_info(pin: str) -> dict[str, Any]:
    key = pin.strip().upper()
    fns = PINS.get(key)
    if not fns:
        return {"pin": key, "found": False, "functions": []}
    return {"pin": key, "found": True, "functions": fns}


def load_board(repo_root: Path, name: str = "bluepill_f103c8") -> dict[str, Any]:
    path = repo_root / "boards" / f"{name}.yaml"
    if not path.is_file():
        return {
            "board": "Blue Pill",
            "mcu": MCU["name"],
            "led": "PC13",
            "oscillator": "8MHz HSE",
            "debug": "SWD",
        }
    text = path.read_text(encoding="utf-8")
    # Minimal YAML subset (key: value) — avoid extra dependency.
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data
