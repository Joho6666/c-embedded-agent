#include "8051_compat.h"

void delay_ms(unsigned int ms) {
    unsigned int i, j;
    for (i = 0; i < ms; i++) {
        for (j = 0; j < 120; j++) {
            /* 11.0592MHz approximate 1ms busy wait loop */
        }
    }
}

void main(void) {
    P1 = 0xFF; /* turn off all LEDs */
    while (1) {
        P1 = 0x00; /* turn on LEDs */
        delay_ms(500);
        P1 = 0xFF; /* turn off LEDs */
        delay_ms(500);
    }
}
