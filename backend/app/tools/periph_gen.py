from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.filesystem import read_file, write_file
from app.tools.hal_modules import register_hal_module


def configure_peripheral(root: Path, kind: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    fn = {
        "usart": configure_usart,
        "adc": configure_adc,
        "pwm": configure_pwm,
        "i2c": configure_i2c,
        "spi": configure_spi,
        "exti": configure_exti,
    }.get(kind)
    if not fn:
        return {"ok": False, "reason": f"unknown peripheral {kind}"}
    import inspect

    params = inspect.signature(fn).parameters
    kwargs = {k: v for k, v in args.items() if k in params and k != "root"}
    return fn(root, **kwargs)


def _add_core_source(root: Path, rel: str) -> None:
    try:
        mk = read_file(root, "Makefile")
    except FileNotFoundError:
        return
    if rel in mk:
        return
    needle = "\tCore/Src/gpio.c \\\n"
    insert = needle + f"\t{rel} \\\n"
    if needle in mk:
        write_file(root, "Makefile", mk.replace(needle, insert, 1), advanced=True)
        return
    mk2, _ = _append_source(mk, rel)
    if mk2 != mk:
        write_file(root, "Makefile", mk2, advanced=True)


def _append_source(makefile: str, rel: str) -> tuple[str, bool]:
    if rel in makefile:
        return makefile, False
    lines = makefile.splitlines(keepends=True)
    last = -1
    for i, line in enumerate(lines):
        if line.strip().endswith(".c \\") or "Core/Src/" in line:
            last = i
    if last < 0:
        return makefile, False
    prev = lines[last]
    if not prev.rstrip("\n").endswith("\\"):
        lines[last] = prev.rstrip("\n") + " \\\n"
        lines.insert(last + 1, f"\t{rel}\n")
    else:
        lines.insert(last + 1, f"\t{rel} \\\n")
    return "".join(lines), True


def _write(root: Path, rel: str, content: str) -> None:
    write_file(root, rel, content)


def configure_usart(root: Path, instance: str = "USART1", baud: int = 115200, mode: str = "polling") -> dict[str, Any]:
    inst = (instance or "USART1").upper()
    baud = int(baud or 115200)
    mode = (mode or "polling").lower()
    tx, rx = ("GPIO_PIN_9", "GPIO_PIN_10") if inst == "USART1" else ("GPIO_PIN_2", "GPIO_PIN_3")
    irq = f"{inst}_IRQn"
    files = []
    _write(
        root,
        "Core/Inc/usart.h",
        f"""#ifndef USART_H
#define USART_H
#ifdef __cplusplus
extern "C" {{
#endif
#include "main.h"
extern UART_HandleTypeDef huart1;
void MX_{inst}_UART_Init(void);
#ifdef __cplusplus
}}
#endif
#endif
""",
    )
    dma_block = ""
    if mode == "dma":
        dma_block = """
  __HAL_RCC_DMA1_CLK_ENABLE();
  hdma_usart1_rx.Instance = DMA1_Channel5;
  hdma_usart1_rx.Init.Direction = DMA_PERIPH_TO_MEMORY;
  hdma_usart1_rx.Init.PeriphInc = DMA_PINC_DISABLE;
  hdma_usart1_rx.Init.MemInc = DMA_MINC_ENABLE;
  hdma_usart1_rx.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
  hdma_usart1_rx.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
  hdma_usart1_rx.Init.Mode = DMA_CIRCULAR;
  hdma_usart1_rx.Init.Priority = DMA_PRIORITY_LOW;
  if (HAL_DMA_Init(&hdma_usart1_rx) != HAL_OK)
  {
    Error_Handler();
  }
  __HAL_LINKDMA(huart, hdmarx, hdma_usart1_rx);
  HAL_NVIC_SetPriority(DMA1_Channel5_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Channel5_IRQn);
"""
    nvic = ""
    if mode in {"interrupt", "it", "dma"}:
        nvic = f"""
  HAL_NVIC_SetPriority({irq}, 0, 0);
  HAL_NVIC_EnableIRQ({irq});
"""
    dma_decl = "DMA_HandleTypeDef hdma_usart1_rx;\n" if mode == "dma" else ""
    _write(
        root,
        "Core/Src/usart.c",
        f"""#include "usart.h"

UART_HandleTypeDef huart1;
{dma_decl}
void MX_{inst}_UART_Init(void)
{{
  huart1.Instance = {inst};
  huart1.Init.BaudRate = {baud};
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {{
    Error_Handler();
  }}
}}

void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{{
  GPIO_InitTypeDef gpio = {{0}};
  if (huart->Instance != {inst})
  {{
    return;
  }}
  __HAL_RCC_{inst}_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  gpio.Pin = {tx};
  gpio.Mode = GPIO_MODE_AF_PP;
  gpio.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOA, &gpio);
  gpio.Pin = {rx};
  gpio.Mode = GPIO_MODE_INPUT;
  gpio.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOA, &gpio);
{nvic}{dma_block}}}
""",
    )
    files.extend(["Core/Inc/usart.h", "Core/Src/usart.c"])
    _add_core_source(root, "Core/Src/usart.c")
    mods = ["UART"]
    if mode == "dma":
        mods.append("DMA")
        _ensure_irq(root, "USART1_IRQHandler", "HAL_UART_IRQHandler(&huart1);", extra_inc="usart.h")
        _ensure_irq(root, "DMA1_Channel5_IRQHandler", "HAL_DMA_IRQHandler(huart1.hdmarx);", extra_inc="usart.h")
    elif mode in {"interrupt", "it"}:
        _ensure_irq(root, "USART1_IRQHandler", "HAL_UART_IRQHandler(&huart1);", extra_inc="usart.h")
    for m in mods:
        register_hal_module(root, m)
    return {"ok": True, "files": files, "instance": inst, "baud": baud, "mode": mode, "halModules": mods}


def configure_adc(root: Path, instance: str = "ADC1", channel: int = 0, mode: str = "polling") -> dict[str, Any]:
    mode = (mode or "polling").lower()
    dma_decl = "DMA_HandleTypeDef hdma_adc1;\n" if mode == "dma" else ""
    dma_msp = ""
    if mode == "dma":
        dma_msp = """
  __HAL_RCC_DMA1_CLK_ENABLE();
  hdma_adc1.Instance = DMA1_Channel1;
  hdma_adc1.Init.Direction = DMA_PERIPH_TO_MEMORY;
  hdma_adc1.Init.PeriphInc = DMA_PINC_DISABLE;
  hdma_adc1.Init.MemInc = DMA_MINC_ENABLE;
  hdma_adc1.Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
  hdma_adc1.Init.MemDataAlignment = DMA_MDATAALIGN_HALFWORD;
  hdma_adc1.Init.Mode = DMA_CIRCULAR;
  hdma_adc1.Init.Priority = DMA_PRIORITY_LOW;
  if (HAL_DMA_Init(&hdma_adc1) != HAL_OK)
  {
    Error_Handler();
  }
  __HAL_LINKDMA(hadc, DMA_Handle, hdma_adc1);
"""
    _write(
        root,
        "Core/Inc/adc.h",
        """#ifndef ADC_H
#define ADC_H
#ifdef __cplusplus
extern "C" {
#endif
#include "main.h"
extern ADC_HandleTypeDef hadc1;
void MX_ADC1_Init(void);
#ifdef __cplusplus
}
#endif
#endif
""",
    )
    _write(
        root,
        "Core/Src/adc.c",
        f"""#include "adc.h"

ADC_HandleTypeDef hadc1;
{dma_decl}
void MX_ADC1_Init(void)
{{
  ADC_ChannelConfTypeDef sConfig = {{0}};
  hadc1.Instance = ADC1;
  hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc1.Init.ContinuousConvMode = {"ENABLE" if mode == "dma" else "DISABLE"};
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 1;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {{
    Error_Handler();
  }}
  sConfig.Channel = ADC_CHANNEL_{int(channel)};
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_55CYCLES_5;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {{
    Error_Handler();
  }}
}}

void HAL_ADC_MspInit(ADC_HandleTypeDef *hadc)
{{
  GPIO_InitTypeDef gpio = {{0}};
  if (hadc->Instance != ADC1)
  {{
    return;
  }}
  __HAL_RCC_ADC1_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  gpio.Pin = GPIO_PIN_{int(channel)};
  gpio.Mode = GPIO_MODE_ANALOG;
  HAL_GPIO_Init(GPIOA, &gpio);
{dma_msp}}}
""",
    )
    _add_core_source(root, "Core/Src/adc.c")
    register_hal_module(root, "ADC")
    if mode == "dma":
        register_hal_module(root, "DMA")
        _ensure_irq(root, "DMA1_Channel1_IRQHandler", "HAL_DMA_IRQHandler(hadc1.DMA_Handle);", extra_inc="adc.h")
    return {"ok": True, "files": ["Core/Inc/adc.h", "Core/Src/adc.c"], "mode": mode, "channel": int(channel)}


def configure_pwm(root: Path, instance: str = "TIM2", channel: int = 1) -> dict[str, Any]:
    _write(
        root,
        "Core/Inc/tim.h",
        """#ifndef TIM_H
#define TIM_H
#ifdef __cplusplus
extern "C" {
#endif
#include "main.h"
extern TIM_HandleTypeDef htim2;
void MX_TIM2_Init(void);
#ifdef __cplusplus
}
#endif
#endif
""",
    )
    _write(
        root,
        "Core/Src/tim.c",
        """#include "tim.h"

TIM_HandleTypeDef htim2;

void MX_TIM2_Init(void)
{
  TIM_OC_InitTypeDef oc = {0};
  __HAL_RCC_TIM2_CLK_ENABLE();
  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 72 - 1;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = 1000 - 1;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_PWM_Init(&htim2) != HAL_OK)
  {
    Error_Handler();
  }
  oc.OCMode = TIM_OCMODE_PWM1;
  oc.Pulse = 500;
  oc.OCPolarity = TIM_OCPOLARITY_HIGH;
  oc.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
}

void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *htim)
{
  GPIO_InitTypeDef gpio = {0};
  if (htim->Instance != TIM2)
  {
    return;
  }
  __HAL_RCC_GPIOA_CLK_ENABLE();
  gpio.Pin = GPIO_PIN_0;
  gpio.Mode = GPIO_MODE_AF_PP;
  gpio.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOA, &gpio);
}
""",
    )
    _add_core_source(root, "Core/Src/tim.c")
    register_hal_module(root, "TIM")
    return {"ok": True, "files": ["Core/Inc/tim.h", "Core/Src/tim.c"], "instance": instance, "channel": channel}


def configure_i2c(root: Path, instance: str = "I2C1") -> dict[str, Any]:
    _write(
        root,
        "Core/Inc/i2c.h",
        """#ifndef I2C_H
#define I2C_H
#ifdef __cplusplus
extern "C" {
#endif
#include "main.h"
extern I2C_HandleTypeDef hi2c1;
void MX_I2C1_Init(void);
#ifdef __cplusplus
}
#endif
#endif
""",
    )
    _write(
        root,
        "Core/Src/i2c.c",
        """#include "i2c.h"

I2C_HandleTypeDef hi2c1;

void MX_I2C1_Init(void)
{
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 100000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
}

void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c)
{
  GPIO_InitTypeDef gpio = {0};
  if (hi2c->Instance != I2C1)
  {
    return;
  }
  __HAL_RCC_I2C1_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  gpio.Pin = GPIO_PIN_6 | GPIO_PIN_7;
  gpio.Mode = GPIO_MODE_AF_OD;
  gpio.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOB, &gpio);
}
""",
    )
    _add_core_source(root, "Core/Src/i2c.c")
    register_hal_module(root, "I2C")
    return {"ok": True, "files": ["Core/Inc/i2c.h", "Core/Src/i2c.c"], "instance": instance}


def configure_spi(root: Path, instance: str = "SPI1") -> dict[str, Any]:
    _write(
        root,
        "Core/Inc/spi.h",
        """#ifndef SPI_H
#define SPI_H
#ifdef __cplusplus
extern "C" {
#endif
#include "main.h"
extern SPI_HandleTypeDef hspi1;
void MX_SPI1_Init(void);
#ifdef __cplusplus
}
#endif
#endif
""",
    )
    _write(
        root,
        "Core/Src/spi.c",
        """#include "spi.h"

SPI_HandleTypeDef hspi1;

void MX_SPI1_Init(void)
{
  hspi1.Instance = SPI1;
  hspi1.Init.Mode = SPI_MODE_MASTER;
  hspi1.Init.Direction = SPI_DIRECTION_2LINES;
  hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
  hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
  hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
  hspi1.Init.NSS = SPI_NSS_SOFT;
  hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;
  hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
  hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi1.Init.CRCPolynomial = 10;
  if (HAL_SPI_Init(&hspi1) != HAL_OK)
  {
    Error_Handler();
  }
}

void HAL_SPI_MspInit(SPI_HandleTypeDef *hspi)
{
  GPIO_InitTypeDef gpio = {0};
  if (hspi->Instance != SPI1)
  {
    return;
  }
  __HAL_RCC_SPI1_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  gpio.Pin = GPIO_PIN_5 | GPIO_PIN_7;
  gpio.Mode = GPIO_MODE_AF_PP;
  gpio.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOA, &gpio);
  gpio.Pin = GPIO_PIN_6;
  gpio.Mode = GPIO_MODE_INPUT;
  gpio.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOA, &gpio);
}
""",
    )
    _add_core_source(root, "Core/Src/spi.c")
    register_hal_module(root, "SPI")
    return {"ok": True, "files": ["Core/Inc/spi.h", "Core/Src/spi.c"], "instance": instance}


def configure_exti(root: Path, pin: str = "PA0", edge: str = "falling") -> dict[str, Any]:
    edge_u = (edge or "falling").lower()
    mode = "GPIO_MODE_IT_RISING" if edge_u == "rising" else "GPIO_MODE_IT_FALLING"
    gpio_c = """#include "gpio.h"

void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef gpio = {0};

  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_AFIO_CLK_ENABLE();

  HAL_GPIO_WritePin(LED_GPIO_Port, LED_Pin, GPIO_PIN_SET);

  gpio.Pin = LED_Pin;
  gpio.Mode = GPIO_MODE_OUTPUT_PP;
  gpio.Pull = GPIO_NOPULL;
  gpio.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LED_GPIO_Port, &gpio);

  gpio.Pin = GPIO_PIN_0;
  gpio.Mode = %s;
  gpio.Pull = GPIO_PULLUP;
  HAL_GPIO_Init(GPIOA, &gpio);

  HAL_NVIC_SetPriority(EXTI0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(EXTI0_IRQn);
}
""" % mode
    _write(root, "Core/Src/gpio.c", gpio_c)
    _ensure_irq(root, "EXTI0_IRQHandler", "HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0);")
    register_hal_module(root, "GPIO")
    register_hal_module(root, "EXTI")
    return {"ok": True, "files": ["Core/Src/gpio.c"], "pin": pin, "edge": edge_u}


def _ensure_irq(root: Path, name: str, body: str, extra_inc: str | None = None) -> None:
    rel = "Core/Src/stm32f1xx_it.c"
    try:
        text = read_file(root, rel)
    except FileNotFoundError:
        return
    if extra_inc and f'#include "{extra_inc}"' not in text:
        text = text.replace('#include "main.h"', f'#include "main.h"\n#include "{extra_inc}"', 1)
    if name not in text:
        text = text.rstrip() + f"\n\nvoid {name}(void)\n{{\n  {body}\n}}\n"
        write_file(root, rel, text)
    hdr = "Core/Inc/stm32f1xx_it.h"
    try:
        h = read_file(root, hdr)
    except FileNotFoundError:
        return
    if name not in h:
        h = h.replace("void SysTick_Handler(void);", f"void SysTick_Handler(void);\nvoid {name}(void);")
        write_file(root, hdr, h)
