import type { ToolItem } from "@/types/tools";

const now = "2026-08-31 14:00";

export const tools: ToolItem[] = [
  { id: "cubemx", name: "STM32CubeMX", category: "Generator", group: "Generator", status: "connected", version: "6.12", executable: "STM32CubeMX", capabilities: ["generate"], permissions: ["write"], lastChecked: now },
  { id: "armgcc", name: "ARM GCC", category: "Compiler", group: "Compiler", status: "connected", version: "13.2.1", executable: "arm-none-eabi-gcc", capabilities: ["compile", "link"], permissions: ["read"], lastChecked: now, detail: "13.2.1" },
  {
    id: "keilmdk",
    name: "Keil MDK / uVision",
    category: "Compiler",
    group: "Compiler",
    status: "connected",
    version: "5.39",
    executable: "C:\\Keil_v5\\UV4\\UV4.exe",
    capabilities: ["compile", "link", "flash"],
    permissions: ["read", "write", "flash"],
    lastChecked: now,
    detail: "V5.39 · UV4.exe",
  },
  { id: "gcc", name: "GCC", category: "Compiler", group: "Compiler", status: "connected", version: "14.2", capabilities: ["compile"], permissions: ["read"], lastChecked: now, detail: "14.2" },
  { id: "keilc51", name: "Keil C51", category: "Compiler", group: "Compiler", status: "disconnected", capabilities: ["compile"], permissions: ["read"], lastChecked: now, detail: "未检测到" },
  { id: "clangd", name: "clangd", category: "Code Intelligence", group: "Code Intelligence", status: "connected", version: "18.1", capabilities: ["diagnostics"], permissions: ["read"], lastChecked: now, detail: "18.1" },
  { id: "cppcheck", name: "Cppcheck", category: "Static Analysis", group: "Static Analysis", status: "connected", version: "2.16", capabilities: ["analyze"], permissions: ["read"], lastChecked: now, detail: "2.16" },
  { id: "unity", name: "Unity", category: "Testing", group: "Testing", status: "connected", capabilities: ["test"], permissions: ["read"], lastChecked: now },
  { id: "ceedling", name: "Ceedling", category: "Testing", group: "Testing", status: "connected", capabilities: ["test"], permissions: ["read"], lastChecked: now },
  { id: "openocd", name: "OpenOCD", category: "Hardware", group: "Hardware", status: "connected", version: "0.12", capabilities: ["flash", "debug"], permissions: ["flash", "debug"], lastChecked: now, detail: "0.12" },
  { id: "stlink", name: "ST-Link", category: "Hardware", group: "Hardware", status: "connected", capabilities: ["flash", "debug"], permissions: ["flash", "debug"], lastChecked: now, detail: "ST-LINK/V2" },
  { id: "cubeprog", name: "STM32CubeProgrammer", category: "Hardware", group: "Hardware", status: "connected", capabilities: ["flash", "erase"], permissions: ["flash", "erase"], lastChecked: now },
  { id: "jlink", name: "J-Link", category: "Hardware", group: "Hardware", status: "disconnected", capabilities: ["flash"], permissions: ["flash"], lastChecked: now },
  { id: "com3", name: "COM3", category: "Serial", group: "Serial", status: "connected", capabilities: ["serial"], permissions: ["read"], lastChecked: now, detail: "115200 baud" },
  { id: "git", name: "Git", category: "Git", group: "Git", status: "connected", version: "2.47", capabilities: ["vcs"], permissions: ["write"], lastChecked: now, detail: "2.47" },
];
