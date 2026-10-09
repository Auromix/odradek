/* SPDX-License-Identifier: CC-BY-NC-4.0 */
.syntax unified
.cpu cortex-m0plus
.thumb
.section .isr_vector,"a",%progbits
.word _estack, Reset_Handler, Default_Handler, Default_Handler
.word 0,0,0,0,0,0,0,Default_Handler,0,0,Default_Handler,SysTick_Handler
.rept 32
.word Default_Handler
.endr
