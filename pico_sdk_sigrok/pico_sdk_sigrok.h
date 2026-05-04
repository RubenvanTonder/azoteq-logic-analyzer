#ifndef PICO_SDK_SIGROK
#define PICO_SDK_SIGROK

/* Includes*/
#include <stdio.h>
#include "pico/stdlib.h" //uart definitions
#include <stdlib.h> //atoi,atol, malloc
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "hardware/adc.h"
#include "hardware/dma.h"
//#include "hardware/sio.h"
#include "hardware/structs/bus_ctrl.h"
#include "hardware/uart.h"
#include "hardware/clocks.h"
#include "pico/multicore.h"
#include "tusb.h"//.tud_cdc_write...
#include "hardware/pwm.h"
#include "hardware/vreg.h"

/* Function to set the duty cycle of the PWM signals*/
void set_pwm_level(uint gpio, uint16_t level);

/* Function to set the frequency of the PWM signals (changes duty cycle the same)*/
// might implement it in order to cahnge frequency only and not duty cycle as well
void update_pwm_frequency(uint pin, uint32_t freq_hz, float duty_percent);

#endif
