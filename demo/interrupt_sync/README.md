# DEMO: Interrupt Synchronization Bug (Motor Controller State Machine)

## Symptom

Motor controller occasionally overshoots the target encoder count, or the
state machine gets stuck in MOTOR_RUNNING and never transitions to
MOTOR_STOPPING, even though the encoder has passed the target.

Behavior is non-deterministic — sometimes it works, sometimes the motor
runs indefinitely until watchdog reset.

## Expected Behavior

Motor stops at exactly the target encoder count every time.

## Root Causes (intentionally introduced)

1. **Missing `volatile`** (`state_machine.c:21`): `g_encoder_count` is modified
   in the encoder ISR but not declared `volatile`. The compiler hoists the value
   into a register in the main loop, so `state_machine_update()` never sees
   ISR updates after the first iteration.

2. **Non-atomic 32-bit access on 8-bit MCU** (`state_machine.c:30`): AVR is an
   8-bit architecture. Reading or writing a 32-bit variable takes 4 separate
   1-byte instructions. If the ISR fires between byte 2 and byte 3 of the read,
   the comparison uses a torn value.

3. **Non-atomic 16-bit fault word** (`state_machine.c:52`): `g_motor_fault = 0xDEAD`
   compiles to two 8-bit stores. An ISR reading this value mid-write sees a
   partially written fault code.

## How to Demo

Load `demo/interrupt_sync/src/` into the copilot.
Symptom: "Motor overshoots target position and state machine gets stuck"
Expected: "Motor stops precisely at target encoder count"
