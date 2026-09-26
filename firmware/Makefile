# Firmware Makefile
# Target: ATmega328P (Arduino Uno)
# Toolchain: avr-gcc

MCU        = atmega328p
F_CPU      = 16000000UL
CC         = avr-gcc
OBJCOPY    = avr-objcopy
AVRDUDE    = avrdude
PORT      ?= /dev/ttyUSB0
BAUD       = 115200
PROGRAMMER = arduino

CFLAGS  = -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=c11 -Wall -Wextra \
          -ffunction-sections -fdata-sections
LDFLAGS = -mmcu=$(MCU) -Wl,--gc-sections

SRCS = main.c keypad.c display.c input_buffer.c
OBJS = $(SRCS:.c=.o)
TARGET = firmware

.PHONY: all clean flash

all: $(TARGET).hex

$(TARGET).elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

flash: $(TARGET).hex
	$(AVRDUDE) -c $(PROGRAMMER) -p $(MCU) -P $(PORT) -b $(BAUD) -U flash:w:$<:i

clean:
	rm -f $(OBJS) $(TARGET).elf $(TARGET).hex
