/* Minimal STM32F103 UART beacon — Renode simulation spike (Level 2).
 * Same MCU as the Blue Pill target; USART1 @ PA9-style usage, LED PC13.
 */
typedef volatile unsigned vu32;

#define USART1_SR (*(vu32 *)0x40013800u)
#define USART1_DR (*(vu32 *)0x40013804u)
#define USART1_CR1 (*(vu32 *)0x4001380Cu)
#define RCC_APB2ENR (*(vu32 *)0x40021018u)
#define GPIOC_ODR (*(vu32 *)0x4001100Cu)

static void putc_(char c)
{
    while (!(USART1_SR & (1u << 7))) {
    } /* TXE */
    USART1_DR = (unsigned)(unsigned char)c;
}

static void puts_(const char *s)
{
    while (*s) {
        putc_(*s++);
    }
}

int main(void)
{
    RCC_APB2ENR |= (1u << 14) | (1u << 4); /* USART1EN | IOPCEN */
    USART1_CR1 |= (1u << 0) | (1u << 3);   /* UE | TE — Renode drops chars without these */
    for (;;) {
        puts_("CEA:SIM:PASS\r\n");
        GPIOC_ODR ^= (1u << 13); /* PC13 blink */
        for (vu32 i = 0; i < 200000u; i++) {
            __asm__("nop");
        }
    }
}

void reset_handler(void);

__attribute__((section(".isr_vector"), used))
void (*const vectors[])(void) = {
    (void (*)(void))0x20005000u, /* initial SP (20K SRAM top) */
    reset_handler,
};

void reset_handler(void)
{
    (void)main();
    for (;;) {
    }
}
