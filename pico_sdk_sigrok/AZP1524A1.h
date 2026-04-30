/******************************************************************************
 * File Name: AZP1524A1.h
 * Description:  H-file for PCB version AZP1524A1
 * Author: Ruben van Tonder     
 * Your NameDate: 2026-04-30
 * Version: 1.0
 * Copyright (c) 2026 Your Azoteq. All rights reserved.
 * GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
 * *****************************************************************************/
#ifndef AZP1524A1
#define AZP1524A1

#define BASE_MODE 0
#define PICO_MODE 0
#define AZO_MODE 1
#define NUM_A_CHAN 2 // number of analog channels
#define NUM_D_CHAN 8 // number of digital channels

//Note: GPIO_D_MASK is relative to the pins of the chip, whereas the
//MEM_D_MASK is relative to the value written in memory, those may be different depending
//on how data is shifted from the GPIOs into memory.
#define GPIO_D_MASK 0x0003FC  //Mask of bits for digital inputs
#define UART_EN 1
#define MEM_D_MASK_L 0x3FC  //lower mask of bits for digital inputs
#define MEM_D_MASK_U 0x0  //upper mask of bits for digital inputs
#define PIN_TEST_MASK 0x001FFC
#define HAS_LED 1
#define LED_PIN 25

// ADC Channel
#define ADC1 41
#define ADC2 42

// GPIO pins used for each digital channel
#define D1 2
#define D2 3
#define D3 4
#define D4 5
#define D5 6
#define D6 7
#define D7 8
#define D8 9

// Level shifter control pins
#define DIR 14
#define NOT_OE 15

// PWM Pins
#define PWM1 12
#define PWM2 13

// RP2350
#define PICO_RP2350 1

#endif /* AZP1524A1*/