"""Named register/address map for read-only diagnosis.

SCB addresses are ARMv7-M (ARMv7-M ARM); STM32F1 peripheral bases are from
RM0008 (STM32F10x reference manual). Used by probe adapters and the
PeripheralHealthCheck layer — read-only by policy.
"""

from __future__ import annotations

from typing import Any

# ARMv7-M System Control Block
SCB: dict[str, str] = {
    "SHCSR": "0xE000ED24",
    "CFSR": "0xE000ED28",
    "HFSR": "0xE000ED2C",
    "MMFAR": "0xE000ED34",
    "BFAR": "0xE000ED38",
    "DBGMCU_IDCODE": "0xE0042000",
}

# CPU registers readable through a debugger
CPU_REGISTERS = ("pc", "sp", "lr", "xpsr")

# STM32F103 (RM0008) peripheral registers relevant to health checks
STM32F1: dict[str, str] = {
    "RCC_CR": "0x40021000",
    "RCC_CFGR": "0x40021004",
    "RCC_APB2ENR": "0x40021018",
    "RCC_APB1ENR": "0x4002101C",
    "GPIOA_CRL": "0x40010800",
    "GPIOA_CRH": "0x40010804",
    "GPIOA_IDR": "0x40010808",
    "GPIOA_ODR": "0x4001080C",
    "GPIOB_CRL": "0x40010C00",
    "GPIOB_ODR": "0x40010C0C",
    "GPIOC_CRL": "0x40011000",
    "GPIOC_CRH": "0x40011004",
    "GPIOC_IDR": "0x40011008",
    "GPIOC_ODR": "0x4001100C",
    "USART1_SR": "0x40013800",
    "USART1_BRR": "0x40013808",
    "USART1_CR1": "0x4001380C",
    "USART2_SR": "0x40004400",
    "USART2_BRR": "0x40004408",
    "TIM2_CR1": "0x40000000",
    "TIM2_CNT": "0x40000008",
    "TIM2_PSC": "0x40000028",
    "TIM2_ARR": "0x4000002C",
    "TIM2_CCR1": "0x40000034",
    "TIM3_CNT": "0x40000408",
    "TIM3_PSC": "0x40000428",
    "TIM3_ARR": "0x4000042C",
    "TIM3_CCR1": "0x40000434",
    "SPI1_CR1": "0x40013000",
    "SPI1_SR": "0x40013008",
    "I2C1_CR1": "0x40005400",
    "I2C1_SR1": "0x40005414",
    "ADC1_DR": "0x4001244C",
}

ALL_ADDRESSES: dict[str, str] = {**SCB, **STM32F1}


def resolve(name: str) -> str | None:
    key = str(name or "").strip().upper()
    return ALL_ADDRESSES.get(key)


def addresses_for(peripheral: str) -> dict[str, str]:
    prefix = f"{peripheral.upper()}_"
    return {k: v for k, v in ALL_ADDRESSES.items() if k.startswith(prefix)}


def summary() -> dict[str, Any]:
    return {"scb": len(SCB), "stm32f1": len(STM32F1), "readOnly": True}
