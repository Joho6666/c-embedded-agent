#include "8051_compat.h"

void delay(unsigned int ms) {
    unsigned int i, j;
    for (i = 0; i < ms; i++) {
        for (j = 0; j < 120; j++) {
        }
    }
}

void main(void) {
    while (1) {
        P1 = 0x00; /* LEDs ON */
        delay(500);
        P1 = 0xFF; /* LEDs OFF */
        delay(500);
    }
}
