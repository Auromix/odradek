// SPDX-License-Identifier: CC-BY-NC-4.0
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "framing.h"
static int send(Framing *f,Effects *e,const char *s,uint32_t t) {
    int result=0;while(*s) { int r=framing_feed(f,e,(unsigned char)*s++,t);if(r)result=r; }return result;
}
int main(void) {
    Effects e;effects_init(&e);Framing f={0};assert(!effects_value(&e,0));
    assert(send(&f,&e,"SET 1000\r\n",0)==1 && effects_value(&e,1)==1000);
    const char *bad[]={"","SET -1","SET 1001","SET 1x","SET 999999999999999999","SET ","set 1","BREATH 199","BREATH 10001","FLASH 20","FLASH 19 20","FLASH 20 10001","FLASH 20 20 x","OFF x"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++){Effects before=e;assert(!effects_command(&e,bad[i],2));assert(!memcmp(&before,&e,sizeof(e)));}
    for(unsigned level=0;level<=1000;level++){char s[32];snprintf(s,sizeof(s),"SET %u",level);assert(effects_command(&e,s,0));assert(effects_value(&e,UINT32_MAX)==level);}
    for(unsigned p=200;p<=10000;p+=1){char s[32];snprintf(s,sizeof(s),"BREATH %u",p);assert(effects_command(&e,s,UINT32_MAX-100));assert(!effects_value(&e,UINT32_MAX-100));assert(effects_value(&e,(UINT32_MAX-100)+p/2)==1000);assert(!effects_value(&e,(UINT32_MAX-100)+p));for(unsigned t=0;t<p;t+=17)assert(effects_value(&e,(UINT32_MAX-100)+t)<=1000);}
    assert(effects_command(&e,"FLASH 20 30",UINT32_MAX-10));assert(effects_value(&e,UINT32_MAX-10)==1000);assert(!effects_value(&e,9));assert(effects_value(&e,39)==1000);
    assert(send(&f,&e,"SET 700\n",0)==1);
    assert(send(&f,&e,"SET ",UINT32_MAX-10)==0);framing_poll(&f,239);assert(f.length==4);framing_poll(&f,240);assert(!f.length);
    assert(send(&f,&e,"OFF\n",242)==1 && !effects_value(&e,242));
    assert(send(&f,&e,"SET 50000000000000000000000000000000000000000000000\n",300)==-1);
    assert(send(&f,&e,"SET 200\n",301)==1 && effects_value(&e,301)==200);
    framing_error(&f,302);assert(send(&f,&e,"OFF\n",303)==-1 && effects_value(&e,303)==200);
    assert(send(&f,&e,"OFF\n",304)==1);
    assert(framing_feed(&f,&e,0xff,305)==0);assert(send(&f,&e,"SET 1\n",306)==-1);
    for(unsigned i=0;i<100000;i++)assert(!framing_feed(&f,&e,'\r',400));
    assert(send(&f,&e,"SET 1000\n",401)==1);
    puts("PASS: ranges, invalid commands, frame overflow/error/recovery, timer wrap, CR flood");
}
