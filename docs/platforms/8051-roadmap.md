# 8051 (STC89C52 / C51) Platform Adapter Architecture Roadmap

> **状态**: **PLANNED** (规划预留，尚未正式支持)  
> **目标**: 证明 `PlatformAdapter` 与 Tool/Skill/Evidence 体系能够无缝泛化到经典 8 位微控制器体系，而无需修改 Agent Runtime 核心。

---

## 1. 为什么选择 8051 作为第三平台候选？

C-Embedded Agent 遵循原则：**“两个平台证明接口，第三个平台证明架构”**。
* **STM32F103**: 32 位 ARM Cortex-M，Makefile + ARM GCC 工具链，CubeF1 官方 HAL。
* **ESP32-S3**: 32 位 Xtensa 双核，CMake + Ninja + ESP-IDF 框架。
* **8051**: 经典 8 位 CISC 架构，Harvard 结构，SFR 寄存器直接映射，内存严重受限（128B~512B 内部 RAM，8KB~64KB Flash），产物为 Intel HEX。

如果本系统能优雅支持 8051，说明底层没有硬编码任何 32 位 ARM/ESP 假设。

---

## 2. 架构适配设计 (Architecture Blueprint)

### 2.1 适配器规划
* `Adapter ID`: `8051-sdcc` (主选开源通道) 与 `8051-keil` (企业/教学通道)
* `Platform`: `8051`
* `Target MCU`: `STC89C52RC` / `AT89C51`
* `Framework`: 寄存器裸机 / 厂商宏定义 (`REG52.H` / `8051.h`)
* `Artifacts`: `firmware.hex` (Intel HEX 格式)

### 2.2 所需子系统清单

| 维度 | SDCC 路线 (`8051-sdcc`) | Keil C51 路线 (`8051-keil`) |
|---|---|---|
| **编译器/链接器** | `sdcc` (跨平台开源) | `C51.exe`, `BL51.exe` / `LX51.exe`, `OH51.exe` |
| **构建系统** | `make` (配合标准 Makefile) | 命令行批处理调用 `UV4.exe -b` 或直接调用 C51/BL51 |
| **烧录工具** | `stcgal` (Python 开源 STC ISP 烧录器) | `stcgal` 或 STC-ISP 命令行通道 |
| **串口协议** | 标配 9600 或 115200 波特率，定时器 1/2 产生波特率 | 同左 |
| **内存模型** | `small` (变量默认放内部 data 空间) | `small` |
| **头文件兼容层** | `__sfr`, `__sbit`, `__interrupt` | `sfr`, `sbit`, `interrupt` (需 `8051_compat.h` 抽象宏) |

---

## 3. PlatformAdapter 接口映射

未来实现 `8051-sdcc` 时，直接实现 `PlatformAdapter` 标准接口：

1. **`detect_project(root)`**:
   * 检测 `project.json` 中 `platform == "8051"` 或 `mcu == "stc89c52"`。
   * 检测源码包含 `#include <reg52.h>` 或 `#include <8051.h>`。
   * 检测 Makefile 目标编译器为 `sdcc` 或 Keil 工程文件 `*.uvproj`。
2. **`create_template(destination, name, board)`**:
   * 从 `templates/8051_sdcc/` 复制标准工程骨架。
   * 包含标准 Makefile、`main.c` (包含 P1/P2 LED 闪烁)、`8051_compat.h`。
3. **`load_context(root)`**:
   * 提供 8051 关键事实：Flash: 8KB, RAM: 512B (256B Data + 256B XData), Clock: 11.0592MHz (典型串口晶振) 或 12MHz。
   * 标记 SFR 寄存器映射与中断向量号 (`0=INT0, 1=T0, 2=INT1, 3=T1, 4=UART`)。
4. **`build(root)`**:
   * 执行 `sdcc --model-small -mmcs51 main.c -o build/firmware.ihx && packihx build/firmware.ihx > build/firmware.hex`。
   * 解析 SDCC 错误诊断（语法错误、RAM 超限、未定义符号）。
5. **`flash(root, device)`**:
   * 调用 `stcgal -P stc89 -p /dev/ttyUSB0 build/firmware.hex`。
6. **`validate_static(root, task)`**:
   * 静态检查：晶振波特率初值计算 (`TH1 = 256 - (11059200 / 12 / 32 / baud)`)、TR1 启动、ES/EA 中断开关。
7. **`hardware_run(root, serial_device, ...)`**:
   * 烧录后通过串口捕获期望标记：`CEA:8051:PASS`。

---

## 4. 专属技能与验证器规划

* **Skills**:
  * `8051-gpio`: P0/P1/P2/P3 准双向口输入输出控制与上拉电阻注意项。
  * `8051-uart`: 定时器 1 Mode 2 自动重装模式产生波特率与 SBUF 缓冲。
  * `8051-timer`: 定时器 0/1 定时中断与计数模式。
  * `8051-exti`: INT0/INT1 外部低电平或下降沿中断触发。
* **Golden Projects 规划**:
  * `8051_led`: P1 口 LED 500ms 翻转。
  * `8051_uart`: 串口回显与 `CEA:8051:PASS` 打印。
  * `8051_timer_interrupt`: 定时器 0 产生精确 1ms 中断滴答。

---

## 5. 发布边界与防忽悠准则

* **严禁宣传已支持 8051**:
  * `PlatformRegistry` 中必须标记为 `status="planned"`。
  * 前端展示必须为 `Planned`，不能显示 `Available`。
  * 缺少硬件时绝不允许虚构烧录通过记录。
