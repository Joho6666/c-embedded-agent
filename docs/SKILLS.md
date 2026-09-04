# STM32 Skill Pack

Skills tell a harness **how to sequence tools**. They do not execute tools.

| Skill | Path |
|---|---|
| stm32-project | `skills/stm32-project/SKILL.md` |
| stm32-gpio | `skills/stm32-gpio/SKILL.md` |
| stm32-usart | `skills/stm32-usart/SKILL.md` |
| stm32-adc | `skills/stm32-adc/SKILL.md` |
| stm32-pwm | `skills/stm32-pwm/SKILL.md` |
| stm32-i2c | `skills/stm32-i2c/SKILL.md` |
| stm32-spi | `skills/stm32-spi/SKILL.md` |
| stm32-dma | `skills/stm32-dma/SKILL.md` |
| stm32-debugging | `skills/stm32-debugging/SKILL.md` |
| stm32-build-flash-validate | `skills/stm32-build-flash-validate/SKILL.md` |

Web Agent recipes remain in `backend/app/skills/stm32f103.json` (runtime JSON, not MCP).

Debug chain: inspect → parse_ioc → build → diagnose → minimal fix → build → flash → serial → validate.

Compile success is not hardware PASS.
