.syntax unified
.cpu cortex-m3
.thumb

.global g_pfnVectors
.global Default_Handler
.global Reset_Handler

.section .isr_vector,"a",%progbits
g_pfnVectors:
  .word _estack
  .word Reset_Handler
  .word NMI_Handler
  .word HardFault_Handler
  .word Default_Handler
  .word Default_Handler
  .word Default_Handler
  .word 0
  .word 0
  .word 0
  .word 0
  .word Default_Handler
  .word Default_Handler
  .word 0
  .word Default_Handler
  .word SysTick_Handler

.weak NMI_Handler
.thumb_set NMI_Handler, Default_Handler
.weak HardFault_Handler
.thumb_set HardFault_Handler, Default_Handler
.weak SysTick_Handler
.thumb_set SysTick_Handler, Default_Handler

.section .text.Default_Handler,"ax",%progbits
Default_Handler:
  b Default_Handler

.section .text.Reset_Handler,"ax",%progbits
.thumb_func
Reset_Handler:
  ldr r0, =_estack
  mov sp, r0
  ldr r0, =_sdata
  ldr r1, =_edata
  ldr r2, =_sidata
1:
  cmp r0, r1
  bcs 2f
  ldr r3, [r2], #4
  str r3, [r0], #4
  b 1b
2:
  ldr r0, =_sbss
  ldr r1, =_ebss
  movs r2, #0
3:
  cmp r0, r1
  bcs 4f
  str r2, [r0], #4
  b 3b
4:
  bl SystemInit
  bl main
  b Default_Handler
