/**
 * keypad.c — 4x4 matrix keypad driver
 *
 * BUG: no hardware debounce delay.  keypad_get_key() returns a key as soon
 *      as any column reads LOW.  A single physical press can cause the
 *      function to return the same key on many consecutive calls while
 *      the mechanical contacts are bouncing (~5–20 ms).
 *
 *      Combined with the fast main() polling loop this means one press
 *      often registers as 2–4 separate key events.
 */

#include "keypad.h"
#include <avr/io.h>
#include <util/delay.h>

/* Keymap: [row][col] */
static const char KEYMAP[4][4] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'}
};

void keypad_init(void)
{
    /* Rows PC0–PC3: outputs */
    DDRC  |=  0x0F;
    PORTC |=  0x0F;   /* drive HIGH (inactive) */

    /* Cols PC4–PC7: inputs with pull-ups */
    DDRC  &= ~0xF0;
    PORTC |=  0xF0;
}

char keypad_get_key(void)
{
    for (uint8_t row = 0; row < 4; row++) {
        /* Drive this row LOW */
        PORTC = (PORTC & 0xF0) | (~(1 << row) & 0x0F);

        /* BUG: _delay_us(10) is insufficient settling time on noisy boards;
         *      some layouts need ≥50 µs before reading columns reliably. */
        _delay_us(10);

        uint8_t cols = (~PINC >> 4) & 0x0F;   /* active-low → active-high */

        /* Restore row HIGH */
        PORTC |= 0x0F;

        if (cols) {
            for (uint8_t col = 0; col < 4; col++) {
                if (cols & (1 << col)) {
                    /* BUG: no debounce wait here — return immediately */
                    return KEYMAP[row][col];
                }
            }
        }
    }
    return '\0';
}
