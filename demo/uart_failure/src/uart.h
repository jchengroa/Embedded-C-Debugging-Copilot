/**
 * demo/uart_failure/src/uart.h
 */
#ifndef UART_H
#define UART_H

#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>

void    uart_init(void);
void    uart_send_string(const char *str);
uint8_t uart_rx_ready(void);
char    uart_read_byte(void);

#endif
