// SPDX-License-Identifier: CC-BY-NC-4.0
#include "vendor/stm32g030xx.h"
#include "effects.h"
#include "framing.h"
static volatile uint32_t milliseconds;
void SysTick_Handler(void) { milliseconds++; }
void Default_Handler(void) { TIM3->CCR1=0;for(;;){} }
static void init_hardware(void) {
    // Explicit HSI16 / 1. Preserve the default SWD pins PA13/PA14.
    RCC->CR|=RCC_CR_HSION;
    while(!(RCC->CR&RCC_CR_HSIRDY)){}
    RCC->CR&=~RCC_CR_HSIDIV;
    RCC->CFGR&=~(RCC_CFGR_SW|RCC_CFGR_HPRE|RCC_CFGR_PPRE);
    while(RCC->CFGR&RCC_CFGR_SWS){}
    RCC->IOPENR|=RCC_IOPENR_GPIOAEN;(void)RCC->IOPENR;
    // Set CCR=0 BEFORE assigning PA6 to its timer.
    RCC->APBENR1|=RCC_APBENR1_TIM3EN|RCC_APBENR1_USART2EN;(void)RCC->APBENR1;
    TIM3->CR1=0;TIM3->PSC=15;TIM3->ARR=999;TIM3->CCR1=0;
    TIM3->CCMR1=(6u<<4)|TIM_CCMR1_OC1PE;TIM3->CCER=TIM_CCER_CC1E;
    TIM3->EGR=TIM_EGR_UG;TIM3->CR1=TIM_CR1_ARPE|TIM_CR1_CEN;
    GPIOA->AFR[0]=(GPIOA->AFR[0]&~((15u<<8)|(15u<<12)|(15u<<24)))|(1u<<8)|(1u<<12)|(1u<<24);
    GPIOA->MODER=(GPIOA->MODER&~((3u<<4)|(3u<<6)|(3u<<12)))|(2u<<4)|(2u<<6)|(2u<<12);
    GPIOA->PUPDR=(GPIOA->PUPDR&~(3u<<6))|(1u<<6); // Idle RX high.
    USART2->CR1=0;USART2->BRR=139;USART2->CR2=0;USART2->CR3=0;
    USART2->CR1=USART_CR1_TE|USART_CR1_RE|USART_CR1_UE; // ~115108 baud at 16MHz.
    SysTick->LOAD=15999;SysTick->VAL=0;SysTick->CTRL=7;
    RCC->CSR|=RCC_CSR_LSION;while(!(RCC->CSR&RCC_CSR_LSIRDY)){}
    IWDG->KR=0xCCCC;IWDG->KR=0x5555;IWDG->PR=6;IWDG->RLR=249;
    while(IWDG->SR){}IWDG->KR=0xAAAA;
}
// Bounded, non-blocking ACK transmission cannot prevent watchdog service.
static const char *reply;static unsigned reply_index;
static void tx_poll(void) {
    if(reply && (USART2->ISR&USART_ISR_TXE_TXFNF)) {
        char c=reply[reply_index++];if(c)USART2->TDR=(uint8_t)c;else reply=0;
    }
}
int main(void) {
    Effects effects;effects_init(&effects);init_hardware();
    Framing frame={0};
    for(;;) {
        uint32_t now=milliseconds;
        framing_poll(&frame,now);
        if(USART2->ISR&(USART_ISR_ORE|USART_ISR_FE|USART_ISR_NE)) {
            USART2->ICR=USART_ICR_ORECF|USART_ICR_FECF|USART_ICR_NECF;
            if(USART2->ISR&USART_ISR_RXNE_RXFNE)(void)USART2->RDR;
            framing_error(&frame,now);
        } else if(USART2->ISR&USART_ISR_RXNE_RXFNE) {
            int result=framing_feed(&frame,&effects,(unsigned char)USART2->RDR,now);
            if(result && !reply) { reply=result>0?"OK\n":"ERR\n";reply_index=0; }
        }
        TIM3->CCR1=effects_value(&effects,now);tx_poll();IWDG->KR=0xAAAA;
    }
}
extern uint32_t _sidata,_sdata,_edata,_sbss,_ebss;
void Reset_Handler(void) {
    uint32_t *s=&_sidata,*d=&_sdata;while(d<&_edata)*d++=*s++;
    for(d=&_sbss;d<&_ebss;d++)*d=0;
    (void)main();for(;;){}
}
