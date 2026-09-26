/**
 * display.c — Seven-segment segment encoding and output
 */

#include "display.h"
#include <avr/io.h>

/*
 * Segment lookup table for digits 0–9.
 * Bit layout: dp g f e d c b a  (MSB → LSB)
 */
static const uint8_t SEG_TABLE[10] = {
    0b00111111,  /* 0: a b c d e f   */
    0b00000110,  /* 1:   b c         */
    0b01011011,  /* 2: a b   d e   g */
    0b01001111,  /* 3: a b c d     g */
    0b01100110,  /* 4:   b c     f g */
    0b01101101,  /* 5: a   c d   f g */
    0b01111101,  /* 6: a   c d e f g */
    0b00000111,  /* 7: a b c         */
    0b01111111,  /* 8: a b c d e f g */
    0b01101111,  /* 9: a b c d   f g */
};

uint8_t digit_to_segments(uint8_t digit)
{
    if (digit > 9) return 0x00;
    return SEG_TABLE[digit];
}

void display_write_segments(uint8_t segs)
{
    /* Segment data on PB0–PB6; preserve PB7 */
    PORTB = (PORTB & 0x80) | (segs & 0x7F);
}
