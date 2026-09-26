/**
 * demo/sensor_error/src/main.c — Temperature Sensor Demo
 * Symptom: Temperature sensor reports values like -50°C or 450°C at room temperature.
 */
#include <avr/io.h>
#include <util/delay.h>
#include "adc.h"
/* stub for demo — real project would use uart.h */
extern void uart_send_string(const char *);

int main(void)
{
    adc_init();
    char buf[32];
    while (1) {
        uint16_t raw = adc_read(0);
        int32_t  celsius = adc_to_celsius(raw);
        __builtin_sprintf(buf, "TEMP=%ld C\r\n", celsius);
        uart_send_string(buf);
        _delay_ms(1000);
    }
}
