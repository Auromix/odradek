// SPDX-License-Identifier: CC-BY-NC-4.0
#include "framing.h"
void framing_poll(Framing *f,uint32_t now) {
    if((f->length||f->discard) && now-f->last_rx>250) { f->length=0;f->discard=0; }
}
void framing_error(Framing *f,uint32_t now) { f->length=0;f->discard=1;f->last_rx=now; }
int framing_feed(Framing *f,Effects *e,unsigned char c,uint32_t now) {
    framing_poll(f,now);f->last_rx=now;
    if(c=='\r')return 0;
    if(c=='\n') {
        f->line[f->length]=0;
        int ok=!f->discard && effects_command(e,f->line,now);
        f->length=0;f->discard=0;return ok?1:-1;
    }
    if(c<32 || c>126 || f->length>=sizeof(f->line)-1)f->discard=1;
    else if(!f->discard)f->line[f->length++]=(char)c;
    return 0;
}
