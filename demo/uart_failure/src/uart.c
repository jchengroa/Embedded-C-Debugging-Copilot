/**
 * demo/uart_failure/src/uart.c
 *
 * BUG SCENARIO: UART communication sends garbled data intermittently.
 *
 * Root causes:
 *  1. TX buffer written in main loop without disabling UART TX interrupt,
 *     causing partial transmission of previous message.
 *  2. Baud rate register calculated with integer truncation error.
 *  3. No flush/drain wait before writing new data.
 */

#include "uart.h"
#include <string.h>

/* TX circular buffer */
#define TX_BUF_SIZE 64
static volatile uint8_t tx_buf[TX_BUF_SIZE];
static volatile uint8_t tx_head = 0;
static volatile uint8_t tx_tail = 0;

/* BUG 1: UBRR calculation uses integer division — rounds down, causing
 *        baud rate error of up to 0.5 baud period at high rates. */
#define BAUD_RATE    115200UL
#define F_CPU        16000000UL
#define UBRR_VALUE   (F_CPU / (16UL * BAUD_RATE) - 1)  /* should use +0.5 rounding */

void uart_init(void)
{
    UBRR0H = (uint8_t)(UBRR_VALUE >> 8);
    UBRR0L = (uint8_t)(UBRR_VALUE);
    UCSR0B = (1 << RXEN0) | (1 << TXEN0) | (1 << UDRIE0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);  /* 8N1 */
}

/* BUG 2: uart_send_string is called from main loop without disabling
 *        the UDRE interrupt. If TX ISR fires mid-copy, tx_head advances
 *        while the loop is still writing, producing interleaved output. */
void uart_send_string(const char *str)
{
    size_t len = strlen(str);
    for (size_t i = 0; i < len; i++) {
        /* BUG: non-atomic check-then-write on tx_head */
        uint8_t next = (tx_head + 1) % TX_BUF_SIZE;
        if (next == tx_tail) break;  /* buffer full — drop rest of message */
        tx_buf[tx_head] = (uint8_t)str[i];
        tx_head = next;              /* BUG: no cli/sei bracket */
    }
}

/* TX Data Register Empty ISR */
ISR(USART_UDRE_vect)
{
    if (tx_head != tx_tail) {
        UDR0 = tx_buf[tx_tail];
        tx_tail = (tx_tail + 1) % TX_BUF_SIZE;
    } else {
        /* Disable UDRE interrupt when buffer empty */
        UCSR0B &= ~(1 << UDRIE0);
    }
}

uint8_t uart_rx_ready(void)
{
    return (UCSR0A & (1 << RXC0)) ? 1 : 0;
}

char uart_read_byte(void)
{
    return UDR0;
}
