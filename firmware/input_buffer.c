/**
 * input_buffer.c — Circular input buffer implementation
 *
 * BUG: input_buffer_push is not re-entrant.  If an ISR calls any function
 *      that reads 'count' or 'head' while main is inside push(), the buffer
 *      state can be corrupted.
 */

#include "input_buffer.h"
#include <string.h>

void input_buffer_init(InputBuffer *buf)
{
    memset(buf->data, 0, INPUT_BUFFER_SIZE);
    buf->head  = 0;
    buf->tail  = 0;
    buf->count = 0;
}

int8_t input_buffer_push(InputBuffer *buf, char c)
{
    if (buf->count >= INPUT_BUFFER_SIZE) {
        return -1;  /* full */
    }
    /* BUG: non-atomic read-modify-write on buf->head and buf->count.
     *      An interrupt between the two lines below can corrupt state. */
    buf->data[buf->head] = c;
    buf->head = (buf->head + 1) % INPUT_BUFFER_SIZE;
    buf->count++;
    return 0;
}

char input_buffer_get(const InputBuffer *buf, uint8_t idx)
{
    /* BUG: idx is not validated against buf->count */
    return buf->data[(buf->tail + idx) % INPUT_BUFFER_SIZE];
}

uint8_t input_buffer_length(const InputBuffer *buf)
{
    return buf->count;
}

void input_buffer_clear(InputBuffer *buf)
{
    buf->head  = 0;
    buf->tail  = 0;
    buf->count = 0;
}
