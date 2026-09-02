# Platform UI Architecture

前端不以 `if (stm32)` / `if (esp32)` 堆页面。所有目标来自 `src/lib/platform/catalog.ts` 的 `PlatformDefinition`。

## 模型

```
PlatformDefinition {
  id, label, architecture
  supported, status: supported | experimental | planned
  frameworks[], toolchains[], boards[]
  flashAdapters[], debugAdapters[]
  serialCapabilities, skills[], toolbarActions[]
}
```

## 当前目录

| id | status | 后端 |
|---|---|---|
| stm32 | supported（仅 F103 HAL Beta） | Build / Flash / Serial / Validate |
| esp32 | planned | UI Preview |
| c51 | planned | UI Preview |
| rp2040 | planned | UI Preview |
| host-c | planned | UI Preview |

STM32F407 作为 STM32 下的 Planned board，不是独立已支持平台。

## Toolbar

`disabledReason(platform, action, liveMode)`：

- 平台没有该 action → disabled +「当前平台暂不支持」
- 平台 Planned → disabled + 后端尚未实现
- DEMO / OFFLINE → 拒绝真实 build/flash
- Debug 按钮可进入页面，页内标明 GDB Not Available

## 状态

`CapabilityStatus = pass | fail | partial | unknown | unavailable | not_tested`

`InstallStatus = available | not_installed | not_configured | unknown`

探测 API：

- `GET /api/environment` 不因 backend 在线把缺工具标成 available
- `GET /api/devices`：ST-LINK 仅在 `st-info --probe` 成功后 Connected；CMSIS-DAP 无 API 则为 Not Detected

## 创建工程

LIVE + STM32F103 + HAL → `POST /api/projects` 复制官方模板。

其他组合只写前端 HardwareContext，并提示 UI Preview。
