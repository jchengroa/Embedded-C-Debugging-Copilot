#ifndef ADC_H
#define ADC_H
#include <stdint.h>
void     adc_init(void);
uint16_t adc_read(uint8_t channel);
int32_t  adc_to_celsius(uint16_t raw);
#endif
