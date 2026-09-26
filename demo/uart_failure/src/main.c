/**
 * demo/uart_failure/src/main.c
 *
 * DEMO PROJECT: UART Communication Failure
 * Symptom: Device sends garbled/interleaved messages over UART.
 */
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include "uart.h"

#define REPORT_INTERVAL_MS 500

int main(void)
{
    uart_init();
    sei();

    uint32_t counter = 0;
    while (1) {
        char msg[32];
        /* BUG: sprintf result may be interleaved with ISR TX if buffer not drained */
        __builtin_sprintf(msg, "COUNT=%lu\r\n", counter++);
        uart_send_string(msg);
        _delay_ms(REPORT_INTERVAL_MS);
    }
}
