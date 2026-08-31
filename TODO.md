# STM32F103 Beta TODO

## P0
- [x] 审计：伪 HAL / 假 Stop / SSE 重复 / 空 Diff / 非流式编译
- [x] Stop 真正 cancel asyncio.Task，停止后禁止写文件
- [x] SSE 单一 queue，event id 不重复
- [x] file_diff 带 before/after；auto Accept / code 等待
- [x] LLM URL 拒绝 localhost / 环回 / 私网
- [x] 官方 STM32CubeF1 模板（cmsis-device-f1 + stm32f1xx-hal-driver）
- [x] Golden LED：Blue Pill PC13
- [x] GCC/LD 错误进入 Problems；终端按行 SSE

## P1
- [x] Context builder + 单 Agent planner
- [x] apply_patch + 写保护
- [x] SQLite FTS5 知识库 + citation
- [x] MCU / Board profile（PC13，USART1 PA9/PA10）
- [x] LED 静态校验
- [x] 20 题 Benchmark + harness
- [x] clangd / cppcheck 可选
- [x] Artifact 下载 API

## P2
- [x] OpenOCD 固定 argv 烧录 + MCU 不匹配拦截
- [x] pyserial 列表端口
- [x] git snapshot / undo run
- [x] Runs SQLite 持久化（不存 API Key）
- [x] GitHub Actions
- [x] README 聚焦 STM32F103
