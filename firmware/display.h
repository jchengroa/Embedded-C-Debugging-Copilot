/**
 * display.h — Seven-segment display driver
 *
 * Segment encoding (common-cathode, active HIGH):
 *
 *      aaa
 *     f   b
 *     f   b
 *      ggg
 *     e   c
 *     e   c
 *      ddd  dp
 *
 *  Bit: 7=dp  6=g  5=f  4=e  3=d  2=c  1=b  0=a
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

#define MAX_DIGITS 4

uint8_t digit_to_segments(uint8_t digit);   /* 0–9 → segment byte */
void    display_write_segments(uint8_t segs);

#endif /* DISPLAY_H */
