CC ?= sdcc
PACKIHX ?= packihx

CFLAGS ?= -mmcs51 --model-small
BUILD_DIR ?= build

SRCS = main.c
OBJS = $(addprefix $(BUILD_DIR)/, $(SRCS:.c=.rel))
TARGET = $(BUILD_DIR)/firmware

all: $(TARGET).hex

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.rel: %.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).ihx: $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@

$(TARGET).hex: $(TARGET).ihx
	$(PACKIHX) $< > $@

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
