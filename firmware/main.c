/**
 * main.c — Seven-Segment Display with 4x4 Matrix Keypad
 * Target: ATmega328P (Arduino Uno)
 *
 * BUG REPORT:
 *   Symptom: Entering "12" on the keypad sometimes displays "1112" or "112"
 *             on the seven-segment display.
 *   Expected: Display shows "12".
 *   Observed: Digits are duplicated/ghost entries appear.
 */

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include <string.h>

#include "keypad.h"
#include "display.h"
#include "input_buffer.h"

/* --------------------------------------------------------------------------
 * Globals
 * -------------------------------------------------------------------------- */

/* Input buffer shared between ISR and main loop — NOT volatile-qualified. */
InputBuffer g_input;        /* BUG: missing volatile; compiler may cache */

/* Display digit buffer — index 0 = most-significant digit */
uint8_t g_display_buf[4];   /* BUG: no mutex / double-buffer around writes */
uint8_t g_display_digits;   /* number of active digits */

/* Multiplexing state (updated by Timer0 ISR) */
uint8_t g_mux_index;

/* --------------------------------------------------------------------------
 * Timer0 ISR — multiplexes the four seven-segment digits @ ~1 kHz
 * -------------------------------------------------------------------------- */
ISR(TIMER0_COMPA_vect)
{
    /* Turn off all digit-select lines (common-cathode: HIGH = off) */
    PORTD |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);

    /* BUG: g_display_digits is read here without ensuring the write in
     *      main() is complete.  If main() is mid-update the ISR may see
     *      a stale value and latch an extra digit. */
    if (g_mux_index < g_display_digits) {
        display_write_segments(g_display_buf[g_mux_index]);
        /* Enable digit select */
        PORTD &= ~(1 << (PD4 + g_mux_index));
    }

    g_mux_index++;
    /* BUG: wrap is against MAX_DIGITS (4) instead of g_display_digits,
     *      so the counter keeps cycling through uninitialised slots when
     *      fewer than 4 digits are active. */
    if (g_mux_index >= MAX_DIGITS) {
        g_mux_index = 0;
    }
}

/* --------------------------------------------------------------------------
 * Keypad scan — polled, called from main loop
 * BUG: no debounce; a single physical press can produce multiple events
 * -------------------------------------------------------------------------- */
static char scan_keypad(void)
{
    return keypad_get_key();   /* returns '\0' if no key pressed */
}

/* --------------------------------------------------------------------------
 * Append a digit character to the input buffer and refresh the display
 * -------------------------------------------------------------------------- */
static void handle_key(char key)
{
    /* BUG: input_buffer_push is not atomic; the ISR can read g_display_buf
     *      while we are in the middle of updating it below. */
    if (input_buffer_push(&g_input, key) != 0) {
        /* buffer full — ignore */
        return;
    }

    /* Rebuild display buffer from input buffer */
    /* BUG: g_display_digits is updated AFTER g_display_buf is written,
     *      but the ISR checks g_display_digits first.  There is a window
     *      where g_display_digits still holds the old count while
     *      g_display_buf already contains the new digit — causing the old
     *      count of digits to be shown with the new segment data. */
    uint8_t len = input_buffer_length(&g_input);
    for (uint8_t i = 0; i < len; i++) {
        g_display_buf[i] = digit_to_segments(input_buffer_get(&g_input, i) - '0');
    }
    g_display_digits = len;   /* should be written first and with sei()/cli() guard */
}

/* --------------------------------------------------------------------------
 * Hardware initialisation
 * -------------------------------------------------------------------------- */
static void hw_init(void)
{
    /* Segment data lines: PB0–PB6 as outputs */
    DDRB |= 0x7F;

    /* Digit select lines: PD4–PD7 as outputs, initially HIGH (off) */
    DDRD  |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);
    PORTD |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);

    keypad_init();
    input_buffer_init(&g_input);

    /* Timer0: CTC, prescaler /64, compare = 249 → 1 ms period @ 16 MHz */
    TCCR0A = (1 << WGM01);
    TCCR0B = (1 << CS01) | (1 << CS00);
    OCR0A  = 249;
    TIMSK0 = (1 << OCIE0A);

    sei();
}

/* --------------------------------------------------------------------------
 * Main loop
 * -------------------------------------------------------------------------- */
int main(void)
{
    hw_init();

    memset(g_display_buf, 0, sizeof(g_display_buf));
    g_display_digits = 0;
    g_mux_index      = 0;

    while (1) {
        char key = scan_keypad();
        if (key != '\0') {
            handle_key(key);
        }
        /* BUG: no delay / debounce here; fast loop causes multiple
         *      handle_key calls for a single key press */
    }
}
