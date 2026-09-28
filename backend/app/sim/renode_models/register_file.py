# Renode PythonPeripheral: plain read-back register file.
# Used for STM32F1 FLASH_ACR, whose LATENCY field HAL_RCC_ClockConfig reads back
# after writing; an unmodelled register would fail that check with HAL_ERROR.

if request.isInit:
    regs = {0x00: 0x30}  # FLASH_ACR reset value (prefetch buffer enabled)
elif request.isRead:
    request.value = regs.get(request.offset, 0)
elif request.isWrite:
    regs[request.offset] = request.value
