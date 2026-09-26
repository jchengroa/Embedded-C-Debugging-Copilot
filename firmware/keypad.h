/**
 * keypad.h — 4x4 Matrix Keypad driver
 * Rows: PC0–PC3 (outputs, driven LOW one at a time)
 * Cols: PC4–PC7 (inputs with pull-ups)
 */

#ifndef KEYPAD_H
#define KEYPAD_H

#include <stdint.h>

void keypad_init(void);
char keypad_get_key(void);   /* returns '\0' if no key is pressed */

#endif /* KEYPAD_H */
