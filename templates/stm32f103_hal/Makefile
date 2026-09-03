TARGET = firmware
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

MCU = -mcpu=cortex-m3 -mthumb
CFLAGS = $(MCU) -Os -ffunction-sections -fdata-sections -Wall -ICore/Inc -IDrivers/CMSIS -IDrivers/STM32F1xx_HAL_Driver/Inc
LDFLAGS = $(MCU) -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -nostartfiles

SRCS = \
	Core/Src/main.c \
	Core/Src/gpio.c \
	Core/Src/stm32f1xx_it.c \
	Core/Src/system_stm32f1xx.c \
	Core/Src/syscalls.c \
	Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal.c \
	startup_stm32f103xb.s

OBJS = $(SRCS:.c=.o)
OBJS := $(OBJS:.s=.o)

all: $(TARGET).elf $(TARGET).hex $(TARGET).bin

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.s
	$(CC) $(MCU) -c $< -o $@

$(TARGET).elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^
	$(SIZE) $@

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f $(OBJS) $(TARGET).elf $(TARGET).hex $(TARGET).bin $(TARGET).map

.PHONY: all clean
