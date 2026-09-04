#include "8051_compat.h"

void uart_init(void) {
    TMOD |= 0x20; /* Timer 1 Mode 2 (8-bit auto-reload) */
    SCON = 0x50;  /* Mode 1, 8-bit UART, enable receiver */
    TH1 = 0xFD;   /* 9600 baud at 11.0592MHz */
    TL1 = 0xFD;
    TR1 = 1;      /* start Timer 1 */
}

void uart_send_char(char c) {
    SBUF = c;
    while (!TI);
    TI = 0;
}

void uart_send_str(const char *s) {
    while (*s) {
        uart_send_char(*s++);
    }
}

void main(void) {
    uart_init();
    uart_send_str("CEA:8051:PASS\r\n");

    while (1) {
        if (RI) {
            char c = SBUF;
            RI = 0;
            uart_send_char(c);
        }
    }
}
