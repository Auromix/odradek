// SPDX-License-Identifier: CC-BY-NC-4.0
#include "effects.h"
static int equal(const char *a,const char *b) { while(*a && *a==*b){a++;b++;}return *a==*b; }
static int prefix(const char *s,const char *p) { while(*p)if(*s++!=*p++)return 0;return 1; }
static int number(const char **s,uint32_t *v) {
    if(**s<'0'||**s>'9')return 0;
    *v=0;unsigned digits=0;
    while(**s>='0'&&**s<='9') { if(++digits>5)return 0;*v=*v*10u+(uint32_t)(*(*s)++-'0'); }
    return 1;
}
void effects_init(Effects *e) { *e=(Effects){0}; }
int effects_command(Effects *e,const char *s,uint32_t now) {
    Effects next={.epoch=now};uint32_t a,b;
    if(equal(s,"OFF")) { *e=next;return 1; }
    if(prefix(s,"SET ")) {
        s+=4;if(!number(&s,&a)||*s||a>1000)return 0;
        next.mode=1;next.level=(uint16_t)a;
    } else if(prefix(s,"BREATH ")) {
        s+=7;if(!number(&s,&a)||*s||a<200||a>10000)return 0;
        next.mode=2;next.period=a;
    } else if(prefix(s,"FLASH ")) {
        s+=6;if(!number(&s,&a)||*s++!=' '||!number(&s,&b)||*s||a<20||a>10000||b<20||b>10000)return 0;
        next.mode=3;next.on_ms=a;next.period=a+b;
    } else return 0;
    *e=next;return 1;
}
uint16_t effects_value(const Effects *e,uint32_t now) {
    if(e->mode==1)return e->level;
    if(e->mode==2) { uint32_t phase=(now-e->epoch)%e->period,half=e->period/2;
        return (uint16_t)(phase<=half ? phase*1000u/half : (e->period-phase)*1000u/(e->period-half)); }
    if(e->mode==3)return (now-e->epoch)%e->period<e->on_ms?1000:0;
    return 0;
}
