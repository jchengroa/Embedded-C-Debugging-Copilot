#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H
#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>

typedef enum {
    MOTOR_IDLE     = 0,
    MOTOR_RUNNING  = 1,
    MOTOR_STOPPING = 2,
    MOTOR_FAULT    = 3,
} MotorState;

extern volatile uint32_t g_encoder_count;
extern volatile uint32_t g_target_count;
extern MotorState g_motor_state;

void state_machine_update(void);
void state_machine_start(uint32_t target);

/* Hardware stubs (implemented per-platform) */
void motor_enable(void);
void motor_disable(void);
void motor_brake(void);
int  motor_speed_zero(void);
int  motor_over_current(void);

#endif
