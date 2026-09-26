/**
 * main_fixed.c — Seven-Segment Display with 4x4 Matrix Keypad (FIXED)
 *
 * Fixes applied:
 *   1. g_input declared volatile so the compiler never caches its members
 *      across ISR boundaries.
 *   2. Atomic display-buffer update: disable Timer0 ISR (cli/sei bracket)
 *      before touching g_display_buf / g_display_digits.
 *   3. g_display_digits written BEFORE the ISR can observe the new count
 *      (write order corrected inside the cli block).
 *   4. g_mux_index wraps on g_display_digits, not the fixed MAX_DIGITS,
 *      so inactive slots are never latched.
 *   5. Keypad debounce: 50 ms blocking delay after a valid key detection,
 *      with a key-release wait to prevent repeat events.
 *   6. Settling time in keypad scan raised to 50 µs.
 */

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include <string.h>

#include "keypad.h"
#include "display.h"
#include "input_buffer.h"

/* --------------------------------------------------------------------------
 * Globals — volatile where shared with ISR
 * -------------------------------------------------------------------------- */

volatile InputBuffer g_input;           /* FIX 1: volatile */

volatile uint8_t g_display_buf[4];
volatile uint8_t g_display_digits;
volatile uint8_t g_mux_index;

/* --------------------------------------------------------------------------
 * Timer0 ISR
 * -------------------------------------------------------------------------- */
ISR(TIMER0_COMPA_vect)
{
    PORTD |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);

    uint8_t digits = g_display_digits;   /* snapshot once */
    if (digits == 0) return;

    if (g_mux_index < digits) {
        display_write_segments(g_display_buf[g_mux_index]);
        PORTD &= ~(1 << (PD4 + g_mux_index));
    }

    g_mux_index++;
    /* FIX 4: wrap on actual digit count, not MAX_DIGITS */
    if (g_mux_index >= digits) {
        g_mux_index = 0;
    }
}

/* --------------------------------------------------------------------------
 * Keypad scan with debounce (FIX 5)
 * -------------------------------------------------------------------------- */
static char scan_keypad(void)
{
    char key = keypad_get_key();
    if (key == '\0') return '\0';

    /* Debounce: wait for the key to be released, then add settling delay */
    _delay_ms(50);
    while (keypad_get_key() != '\0') { /* wait for release */ }
    _delay_ms(10);

    return key;
}

/* --------------------------------------------------------------------------
 * Append a digit to the input buffer and refresh the display atomically
 * -------------------------------------------------------------------------- */
static void handle_key(char key)
{
    /* Work on a local copy so the ISR is unaffected during preparation */
    uint8_t new_buf[MAX_DIGITS];
    uint8_t new_len;

    /* Temporarily disable Timer0 compare interrupt for the buffer read */
    cli();
    uint8_t old_len = (uint8_t)g_input.count;
    cli();   /* already off — harmless; just a reminder */

    if (old_len >= INPUT_BUFFER_SIZE) {
        sei();
        return;
    }

    /* Push to local shadow first */
    char shadow[INPUT_BUFFER_SIZE];
    for (uint8_t i = 0; i < old_len; i++) {
        shadow[i] = g_input.data[(g_input.tail + i) % INPUT_BUFFER_SIZE];
    }
    shadow[old_len] = key;
    new_len = old_len + 1;
    sei();

    /* Build segment data from shadow */
    for (uint8_t i = 0; i < new_len; i++) {
        new_buf[i] = digit_to_segments(shadow[i] - '0');
    }

    /* FIX 2 & 3: Atomic update — ISR is blocked during the critical section.
     * Write g_display_digits = 0 first so the ISR sees an empty display
     * rather than a half-updated buffer. */
    cli();
    g_display_digits = 0;           /* ISR will skip display while we update */
    for (uint8_t i = 0; i < new_len; i++) {
        g_display_buf[i] = new_buf[i];
    }
    g_mux_index    = 0;
    /* Commit — ISR can now latch the full, consistent state */
    g_display_digits = new_len;
    /* Also push to the real input buffer */
    input_buffer_push((InputBuffer *)&g_input, key);
    sei();
}

/* --------------------------------------------------------------------------
 * Hardware initialisation
 * -------------------------------------------------------------------------- */
static void hw_init(void)
{
    DDRB |= 0x7F;

    DDRD  |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);
    PORTD |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);

    keypad_init();
    input_buffer_init((InputBuffer *)&g_input);

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

    memset((void *)g_display_buf, 0, sizeof(g_display_buf));
    g_display_digits = 0;
    g_mux_index      = 0;

    while (1) {
        char key = scan_keypad();   /* blocks on debounce internally */
        if (key != '\0') {
            handle_key(key);
        }
    }
}
