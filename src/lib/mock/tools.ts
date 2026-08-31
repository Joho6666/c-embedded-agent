import type { ToolItem } from "@/types/tools";

export const tools: ToolItem[] = [
  { id: "armgcc", name: "ARM GCC", group: "Compiler", status: "connected", detail: "13.2.1" },
  { id: "gcc", name: "GCC", group: "Compiler", status: "connected", detail: "14.2" },
  { id: "keilc51", name: "Keil C51", group: "Compiler", status: "disconnected" },
  { id: "iar", name: "IAR", group: "Compiler", status: "disconnected" },
  { id: "clangd", name: "clangd", group: "Code Intelligence", status: "connected", detail: "18.1" },
  { id: "treesitter", name: "Tree-sitter", group: "Code Intelligence", status: "connected" },
  { id: "cppcheck", name: "Cppcheck", group: "Static Analysis", status: "connected", detail: "2.16" },
  { id: "tidy", name: "clang-tidy", group: "Static Analysis", status: "disconnected" },
  { id: "unity", name: "Unity", group: "Testing", status: "connected" },
  { id: "ceedling", name: "Ceedling", group: "Testing", status: "connected" },
  { id: "openocd", name: "OpenOCD", group: "Hardware", status: "connected", detail: "0.12" },
  { id: "stlink", name: "ST-Link", group: "Hardware", status: "connected", detail: "ST-LINK/V2" },
  { id: "jlink", name: "J-Link", group: "Hardware", status: "disconnected" },
  { id: "com3", name: "COM3", group: "Serial", status: "connected", detail: "115200 baud" },
  { id: "git", name: "Git", group: "Git", status: "connected", detail: "2.47" },
];
