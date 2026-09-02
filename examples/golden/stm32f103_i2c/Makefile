TARGET = firmware
CC = arm-none-eabi-gcc
AS = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

MCU = -mcpu=cortex-m3 -mthumb
DEFS = -DSTM32F103xB -DUSE_HAL_DRIVER
INCLUDES = \
	-ICore/Inc \
	-IDrivers/CMSIS/Include \
	-IDrivers/CMSIS/Device/ST/STM32F1xx/Include \
	-IDrivers/STM32F1xx_HAL_Driver/Inc \
	-IDrivers/STM32F1xx_HAL_Driver/Inc/Legacy

CFLAGS = $(MCU) $(DEFS) $(INCLUDES) -Os -ffunction-sections -fdata-sections -Wall -fno-common -g
ASFLAGS = $(MCU) -c
LDFLAGS = $(MCU) -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -Wl,-Map=$(TARGET).map --specs=nano.specs --specs=nosys.specs -Wl,--no-warn-rwx-segments

C_SOURCES = \
	Core/Src/main.c \
	Core/Src/gpio.c \
	Core/Src/i2c.c \
	Core/Src/stm32f1xx_it.c \
	Core/Src/system_stm32f1xx.c \
	Core/Src/syscalls.c \
	Core/Src/stm32f1xx_hal_msp.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_rcc.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_rcc_ex.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_cortex.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_dma.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_flash.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_flash_ex.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_pwr.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_exti.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_usart.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_tim.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_tim_ex.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_adc.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_adc_ex.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_i2c.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_spi.c

ASM_SOURCES = startup_stm32f103xb.s

OBJS = $(C_SOURCES:.c=.o) $(ASM_SOURCES:.s=.o)

all: $(TARGET).elf $(TARGET).hex $(TARGET).bin

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.s
	$(AS) $(ASFLAGS) $< -o $@

$(TARGET).elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)
	$(SIZE) $@

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f $(OBJS) $(TARGET).elf $(TARGET).hex $(TARGET).bin $(TARGET).map

.PHONY: all clean
