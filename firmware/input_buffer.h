/**
 * input_buffer.h — Circular input buffer for keypad characters
 */

#ifndef INPUT_BUFFER_H
#define INPUT_BUFFER_H

#include <stdint.h>

#define INPUT_BUFFER_SIZE 8

typedef struct {
    char    data[INPUT_BUFFER_SIZE];
    uint8_t head;   /* write index */
    uint8_t tail;   /* read index  */
    uint8_t count;
} InputBuffer;

void    input_buffer_init(InputBuffer *buf);
int8_t  input_buffer_push(InputBuffer *buf, char c);   /* returns 0 on success, -1 if full */
char    input_buffer_get(const InputBuffer *buf, uint8_t idx);
uint8_t input_buffer_length(const InputBuffer *buf);
void    input_buffer_clear(InputBuffer *buf);

#endif /* INPUT_BUFFER_H */
