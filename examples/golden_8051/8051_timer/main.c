#include "8051_compat.h"

volatile unsigned int tick_count = 0;

void timer0_isr(void) INTERRUPT(1) {
    TH0 = 0xFC; /* 1ms reload at 11.0592MHz (approx 65536 - 921) */
    TL0 = 0x66;
    tick_count++;
    if (tick_count >= 500) {
        P1 ^= 0x01; /* toggle P1.0 every 500ms */
        tick_count = 0;
    }
}

void timer0_init(void) {
    TMOD &= 0xF0;
    TMOD |= 0x01; /* Timer 0 Mode 1 (16-bit) */
    TH0 = 0xFC;
    TL0 = 0x66;
    ET0 = 1;      /* enable Timer 0 interrupt */
    EA = 1;       /* enable global interrupts */
    TR0 = 1;      /* start Timer 0 */
}

void main(void) {
    timer0_init();
    while (1) {
        /* idle loop driven by timer ISR */
    }
}
