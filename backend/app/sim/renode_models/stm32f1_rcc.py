# Renode PythonPeripheral: STM32F1 RCC with oscillator/PLL ready handshakes.
#
# Renode's stock stm32f103.repl tags RCC_CR as a constant (PLLRDY always set),
# so STM32CubeF1 HAL_RCC_OscConfig spins forever waiting for the PLL to stop.
# Ready bits here follow their enable bits and CFGR.SWS mirrors CFGR.SW, which
# is what the HAL polls. Other registers (APBxENR, ...) read back what was written.
#
# `request` is supplied by Renode; state lives in module globals between calls.

CR, CFGR = 0x00, 0x04
HSION, HSIRDY = 1 << 0, 1 << 1
HSEON, HSERDY = 1 << 16, 1 << 17
PLLON, PLLRDY = 1 << 24, 1 << 25

if request.isInit:
    regs = {CR: HSION | HSIRDY | 0x80, CFGR: 0}
elif request.isRead:
    request.value = regs.get(request.offset, 0)
elif request.isWrite:
    value = request.value
    if request.offset == CR:
        ready = 0
        if value & HSION:
            ready |= HSIRDY
        if value & HSEON:
            ready |= HSERDY
        if value & PLLON:
            ready |= PLLRDY
        value = (value & ~(HSIRDY | HSERDY | PLLRDY)) | ready
    elif request.offset == CFGR:
        value = (value & ~0xC) | ((value & 0x3) << 2)
    regs[request.offset] = value
