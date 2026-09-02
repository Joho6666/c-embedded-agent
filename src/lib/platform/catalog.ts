import type { PlatformDefinition, PlatformId, ToolbarActionId } from "@/types/platform";

const MCU_SKILLS = [
  "GPIO",
  "UART",
  "PWM",
  "TIMER",
  "ADC",
  "DMA",
  "I2C",
  "SPI",
  "CAN",
  "RTC",
  "WDT",
];

const WIRELESS_SKILLS = [...MCU_SKILLS, "Wi-Fi", "BLE", "FreeRTOS"];

export const PLATFORMS: PlatformDefinition[] = [
  {
    id: "stm32",
    label: "STM32",
    architecture: "ARM Cortex-M",
    supported: true,
    status: "supported",
    statusNote: "仅 STM32F103 HAL 为 Beta。F407 及其他系列 Planned。",
    frameworks: [
      { id: "HAL", label: "HAL", status: "supported" },
      { id: "LL", label: "LL", status: "planned" },
      { id: "CMSIS", label: "CMSIS", status: "planned" },
    ],
    toolchains: [
      { id: "ARM_GCC", label: "GNU Arm Embedded", status: "supported" },
      { id: "KEIL", label: "Keil", status: "planned" },
    ],
    boards: [
      {
        id: "bluepill",
        label: "Blue Pill",
        mcu: "STM32F103C8T6",
        architecture: "Cortex-M3",
        clock: "72 MHz",
        flashKb: 64,
        ramKb: 20,
        package: "LQFP48",
        status: "supported",
      },
      {
        id: "f407",
        label: "STM32F407 Discovery",
        mcu: "STM32F407VGT6",
        architecture: "Cortex-M4",
        clock: "168 MHz",
        flashKb: 1024,
        ramKb: 192,
        package: "LQFP100",
        status: "planned",
      },
    ],
    flashAdapters: [
      { id: "stlink", label: "ST-LINK", status: "supported" },
      { id: "openocd", label: "OpenOCD", status: "supported" },
      { id: "cubeprog", label: "STM32CubeProgrammer", status: "planned" },
    ],
    debugAdapters: [
      { id: "stlink", label: "ST-LINK", status: "experimental" },
      { id: "cmsis-dap", label: "CMSIS-DAP", status: "planned" },
      { id: "jlink", label: "J-Link", status: "planned" },
      { id: "openocd", label: "OpenOCD", status: "experimental" },
    ],
    serialCapabilities: true,
    skills: [...MCU_SKILLS, "FreeRTOS"],
    toolbarActions: ["build", "flash", "run", "debug", "serial", "validate", "stop"],
    defaultMcu: "STM32F103C8T6",
    defaultBoard: "Blue Pill",
    defaultFramework: "HAL",
    defaultToolchain: "ARM_GCC",
  },
  {
    id: "esp32",
    label: "ESP32",
    architecture: "Xtensa / RISC-V",
    supported: false,
    status: "planned",
    statusNote: "UI Preview。后端编译 / 烧录尚未实现。",
    frameworks: [{ id: "ESP-IDF", label: "ESP-IDF", status: "planned" }],
    toolchains: [
      { id: "XTENSA_GCC", label: "Xtensa GCC", status: "planned" },
      { id: "RISCV_GCC", label: "RISC-V GCC", status: "planned" },
    ],
    boards: [
      {
        id: "esp32-s3",
        label: "ESP32-S3",
        mcu: "ESP32-S3",
        architecture: "Xtensa LX7",
        clock: "240 MHz",
        flashKb: 8192,
        ramKb: 512,
        status: "planned",
      },
    ],
    flashAdapters: [{ id: "esptool", label: "esptool", status: "planned" }],
    debugAdapters: [{ id: "openocd", label: "OpenOCD", status: "planned" }],
    serialCapabilities: true,
    skills: WIRELESS_SKILLS,
    toolbarActions: ["build", "flash", "monitor", "debug", "validate", "stop"],
    defaultMcu: "ESP32-S3",
    defaultBoard: "ESP32-S3",
    defaultFramework: "ESP-IDF",
    defaultToolchain: "XTENSA_GCC",
  },
  {
    id: "c51",
    label: "C51 / 8051",
    architecture: "8051",
    supported: false,
    status: "planned",
    statusNote: "UI Preview。Keil C51 / SDCC 后端尚未实现。",
    frameworks: [
      { id: "KEIL_C51", label: "Keil C51", status: "planned" },
      { id: "SDCC", label: "SDCC", status: "planned" },
    ],
    toolchains: [
      { id: "SDCC", label: "SDCC", status: "planned" },
      { id: "KEIL", label: "Keil", status: "planned" },
    ],
    boards: [
      {
        id: "stc89c52",
        label: "STC89C52",
        mcu: "STC89C52RC",
        architecture: "8051",
        clock: "11.0592 MHz",
        flashKb: 8,
        ramKb: 0.5,
        status: "planned",
      },
    ],
    flashAdapters: [{ id: "stc-isp", label: "STC ISP", status: "planned" }],
    debugAdapters: [{ id: "keil", label: "Keil", status: "planned" }],
    serialCapabilities: true,
    skills: ["GPIO", "UART", "TIMER", "ADC", "I2C", "SPI", "WDT"],
    toolbarActions: ["build", "hex", "flash", "serial", "stop"],
    defaultMcu: "STC89C52RC",
    defaultBoard: "STC89C52",
    defaultFramework: "SDCC",
    defaultToolchain: "SDCC",
  },
  {
    id: "rp2040",
    label: "RP2040",
    architecture: "ARM Cortex-M0+",
    supported: false,
    status: "planned",
    statusNote: "UI Preview。Pico SDK 后端尚未实现。",
    frameworks: [{ id: "PICO_SDK", label: "Pico SDK", status: "planned" }],
    toolchains: [{ id: "ARM_GCC", label: "GNU Arm Embedded", status: "planned" }],
    boards: [
      {
        id: "pico",
        label: "Raspberry Pi Pico",
        mcu: "RP2040",
        architecture: "Cortex-M0+",
        clock: "133 MHz",
        flashKb: 2048,
        ramKb: 264,
        status: "planned",
      },
    ],
    flashAdapters: [{ id: "picotool", label: "picotool", status: "planned" }],
    debugAdapters: [{ id: "cmsis-dap", label: "CMSIS-DAP", status: "planned" }],
    serialCapabilities: true,
    skills: MCU_SKILLS,
    toolbarActions: ["build", "flash", "serial", "debug", "stop"],
    defaultMcu: "RP2040",
    defaultBoard: "Raspberry Pi Pico",
    defaultFramework: "PICO_SDK",
    defaultToolchain: "ARM_GCC",
  },
  {
    id: "host-c",
    label: "Host C",
    architecture: "Host",
    supported: false,
    status: "planned",
    statusNote: "UI Preview。Host GCC/Clang 工程后端尚未实现。",
    frameworks: [{ id: "POSIX", label: "POSIX / CMake", status: "planned" }],
    toolchains: [
      { id: "GCC", label: "GCC", status: "planned" },
      { id: "CLANG", label: "Clang", status: "planned" },
    ],
    boards: [
      {
        id: "host",
        label: "Host",
        mcu: "Host",
        architecture: "x86_64 / arm64",
        clock: "—",
        flashKb: 0,
        ramKb: 0,
        status: "planned",
      },
    ],
    flashAdapters: [],
    debugAdapters: [{ id: "gdb", label: "GDB", status: "planned" }],
    serialCapabilities: false,
    skills: [],
    toolbarActions: ["build", "run", "test", "debug", "analyze", "stop"],
    defaultMcu: "Host",
    defaultBoard: "Host",
    defaultFramework: "POSIX",
    defaultToolchain: "GCC",
  },
];

export function getPlatform(id: PlatformId | string | undefined): PlatformDefinition {
  const found = PLATFORMS.find((p) => p.id === id);
  return found ?? PLATFORMS[0];
}

export function normalizePlatformId(raw: string | undefined | null): PlatformId {
  const s = (raw ?? "").toLowerCase().replace(/[\s_]/g, "-");
  if (s === "esp32") return "esp32";
  if (s === "8051" || s === "c51" || s === "c51-8051") return "c51";
  if (s === "rp2040") return "rp2040";
  if (s === "linux" || s === "host" || s === "host-c" || s === "hostc") return "host-c";
  return "stm32";
}

export function actionSupported(platform: PlatformDefinition, action: ToolbarActionId): boolean {
  return platform.toolbarActions.includes(action) && (action === "stop" || platform.supported || action === "build");
}

export function actionBackendReady(platform: PlatformDefinition, action: ToolbarActionId): boolean {
  if (action === "stop") return true;
  if (!platform.supported) return false;
  return ["build", "run", "flash", "serial", "validate"].includes(action);
}
