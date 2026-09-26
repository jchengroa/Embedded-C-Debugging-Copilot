/**
 * demo/sensor_error/src/adc.c
 *
 * BUG SCENARIO: Sensor reports wildly incorrect values.
 *
 * Root causes:
 *  1. ADC channel not settled before reading (missing dummy read).
 *  2. Integer overflow in temperature conversion formula.
 *  3. ADC result read in two separate byte reads without ensuring
 *     the high byte is latched (ADCL must be read first on AVR).
 */

#include "adc.h"
#include <avr/io.h>
#include <util/delay.h>

void adc_init(void)
{
    /* AVCC reference, channel 0 */
    ADMUX  = (1 << REFS0);
    /* Enable ADC, prescaler /128 */
    ADCSRA = (1 << ADEN) | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);

    /* BUG: no dummy conversion after enabling ADC.
     * First result after enable is often incorrect on real hardware. */
}

uint16_t adc_read(uint8_t channel)
{
    /* Select channel */
    ADMUX = (ADMUX & 0xF0) | (channel & 0x0F);

    /* BUG: insufficient settling time after channel switch —
     * need at least 1 ADC clock cycle before starting conversion. */
    _delay_us(1);   /* should be at least 10-100 µs depending on source impedance */

    /* Start conversion */
    ADCSRA |= (1 << ADSC);
    while (ADCSRA & (1 << ADSC));   /* wait */

    /* BUG: On AVR, ADCL must be read BEFORE ADCH to latch the result.
     * Reading ADCH first may return the high byte of the previous
     * conversion if another conversion started between reads. */
    uint8_t high = ADCH;   /* WRONG ORDER */
    uint8_t low  = ADCL;
    return ((uint16_t)high << 8) | low;
}

int32_t adc_to_celsius(uint16_t raw)
{
    /* NTC thermistor linearization — simplified Steinhart-Hart approximation.
     *
     * BUG: intermediate calculation overflows int16_t.
     * (raw * 500) with raw up to 1023 → 511500, which overflows int16_t (max 32767).
     * The result is silently truncated, producing wrong temperature values. */
    int16_t temp = (int16_t)((raw * 500) / 1023) - 50;  /* should use int32_t */
    return (int32_t)temp;
}
