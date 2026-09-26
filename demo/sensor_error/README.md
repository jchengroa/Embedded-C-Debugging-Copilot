# DEMO: Sensor Reading Error

## Symptom

Temperature sensor reports impossible values (-50°C or 450°C) at room
temperature (~22°C). Values are wrong on first reading, then sometimes
correct, then wrong again.

## Expected Behavior

Sensor returns values within plausible range for environment (0–50°C).

## Root Causes (intentionally introduced)

1. **Wrong ADC byte read order** (`adc.c:42–44`): AVR requires ADCL to be
   read before ADCH to latch the 10-bit result. Reading ADCH first returns
   a stale high byte.

2. **Integer overflow in conversion** (`adc.c:54`): `raw * 500` overflows
   `int16_t` for any raw ADC value above 65. Result is truncated to a small
   or negative number.

3. **Missing settling time after channel switch** (`adc.c:33`): Only 1 µs
   delay; high-impedance sensor sources need 100+ µs to charge the S/H
   capacitor.

## How to Demo

Load `demo/sensor_error/src/` into the copilot.
Symptom: "Sensor reports -50°C or 450°C at room temperature"
