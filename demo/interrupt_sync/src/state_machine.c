/**
 * demo/interrupt_sync/src/state_machine.c
 *
 * BUG SCENARIO: Motor controller state machine gets stuck or transitions
 * to wrong state because a flag shared between ISR and main loop is
 * not volatile and not atomically accessed.
 *
 * Root causes:
 *  1. g_encoder_count is modified in the encoder ISR and read in main
 *     without volatile — compiler caches value in register.
 *  2. State transition check reads g_encoder_count + g_target_count in
 *     separate reads; ISR can change g_encoder_count between the two,
 *     causing the comparison to use stale data.
 *  3. g_motor_fault is written as a uint16_t from two separate 8-bit
 *     writes on an 8-bit MCU — torn write visible to ISR.
 */

#include "state_machine.h"

/* BUG: missing volatile on ISR-shared variables */
uint32_t g_encoder_count = 0;
uint32_t g_target_count  = 1000;
uint16_t g_motor_fault   = 0;     /* BUG: 16-bit on 8-bit MCU — not atomic */

MotorState g_motor_state = MOTOR_IDLE;

/* Encoder quadrature ISR */
ISR(INT0_vect)
{
    /* BUG: 32-bit increment is not atomic on 8-bit AVR.
     * Read-modify-write of g_encoder_count takes multiple instructions. */
    g_encoder_count++;
}

void state_machine_update(void)
{
    switch (g_motor_state) {
        case MOTOR_IDLE:
            break;

        case MOTOR_RUNNING:
            /* BUG: g_encoder_count is read here without cli/sei.
             * If ISR fires between the two reads below, the comparison
             * uses an inconsistent snapshot. */
            if (g_encoder_count >= g_target_count) {
                g_motor_state = MOTOR_STOPPING;
                motor_brake();
            }
            /* BUG: fault word written as two separate byte stores on AVR;
             * ISR reading g_motor_fault may see half-written value. */
            if (motor_over_current()) {
                g_motor_fault = 0xDEAD;   /* non-atomic on 8-bit MCU */
                g_motor_state = MOTOR_FAULT;
            }
            break;

        case MOTOR_STOPPING:
            if (motor_speed_zero()) {
                g_motor_state = MOTOR_IDLE;
            }
            break;

        case MOTOR_FAULT:
            motor_disable();
            break;
    }
}

void state_machine_start(uint32_t target)
{
    g_target_count = target;
    /* BUG: g_encoder_count not reset atomically */
    g_encoder_count = 0;
    g_motor_state = MOTOR_RUNNING;
    motor_enable();
}
