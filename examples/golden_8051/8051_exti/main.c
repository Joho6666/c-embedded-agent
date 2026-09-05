#include "8051_compat.h"

volatile unsigned char exti_flag = 0;

void exti0_isr(void) INTERRUPT(0) {
    P1 ^= 0x01; /* toggle P1.0 on external interrupt */
    exti_flag = 1;
}

void exti0_init(void) {
    IT0 = 1; /* Trigger on falling edge (IT0=1: falling edge, IT0=0: low level) */
    EX0 = 1; /* Enable External Interrupt 0 */
    EA = 1;  /* Enable global interrupts */
}

void main(void) {
    exti0_init();
    while (1) {
        /* idle loop; wait for INT0 falling edge on P3.2 */
    }
}
