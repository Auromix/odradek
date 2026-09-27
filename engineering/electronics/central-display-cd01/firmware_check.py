#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Compile and execute register transport mock, including split-driver failure."""
from pathlib import Path
import csv,json,subprocess,shutil,tempfile,hashlib
D=Path(__file__).resolve().parent;p=list(csv.DictReader((D/'pixel-map.csv').open()))
code='''#include <assert.h>
#include <string.h>
#include "cd01_example.h"
static uint8_t regs[2][1024];static int fail=-1,corrupt=-1,edges=0;
static int wr(unsigned d,uint16_t a,const uint8_t*p,size_t n){assert(d<2&&a+n<=1024);if((int)d==fail)return -1;memcpy(regs[d]+a,p,n);return 0;}
static int rd(unsigned d,uint16_t a,uint8_t*p,size_t n){assert(d<2&&a+n<=1024);memcpy(p,regs[d]+a,n);if((int)d==corrupt)p[0]^=1;return 0;}
static void syncio(int x){assert(x==0||x==1);edges+=x;}static void wait_us(uint32_t t){assert(t>=100);}
int main(void){cd01_io io={wr,rd,syncio,wait_us};unsigned dot[285]={DOT};unsigned chip[285]={CHIP};uint16_t pixels[285];
memset(regs,0xA5,sizeof regs);assert(!cd01_init_dark(&io));assert(edges==0);
for(unsigned d=0;d<2;d++){assert(regs[d][0]==1&&regs[d][1]==0x5c&&regs[d][4]==0x51&&regs[d][5]==0);unsigned total=0;
for(unsigned i=0;i<198;i++){unsigned en=(regs[d][0x43+3*(i/18)+(i%18)/8]>>((i%18)%8))&1;assert(regs[d][0x100+i]==(en?255:0));total+=en;}assert(total==(d?143:142));
for(unsigned i=0;i<396;i++)assert(regs[d][0x200+i]==0);}
for(unsigned i=0;i<285;i++)pixels[i]=(uint16_t)(0x1234+i);
assert(!cd01_stage_frame(&io,pixels,19));assert(edges==0);
unsigned fitted[2][198]={{0}};for(unsigned i=0;i<285;i++){unsigned d=chip[i],a=dot[i];assert(!fitted[d][a]);fitted[d][a]=1;assert(regs[d][0x200+2*a]==(uint8_t)pixels[i]&&regs[d][0x201+2*a]==(uint8_t)(pixels[i]>>8));}
for(unsigned d=0;d<2;d++){assert(regs[d][4]==0x51&&regs[d][5]==19);for(unsigned i=0;i<198;i++)if(!fitted[d][i])assert(!regs[d][0x200+2*i]&&!regs[d][0x201+2*i]);}
cd01_commit_shared_vsync(&io);assert(edges==1);
for(unsigned a=0;a<1024;a++){uint8_t h[2];assert(!cd01_spi_header(a,1,h));assert(h[0]==a/4&&h[1]==((a%4)*64+32));assert(!cd01_spi_header(a,0,h));assert(h[0]==a/4&&h[1]==(a%4)*64);}uint8_t h[2];assert(cd01_spi_header(1024,1,h)<0);
for(int d=0;d<2;d++){fail=d;assert(cd01_stage_frame(&io,pixels,19)<0);assert(cd01_init_dark(&io)<0);assert(edges==1);}fail=-1;
for(int d=0;d<2;d++){corrupt=d;assert(cd01_init_dark(&io)<0);}return 0;}
'''.replace('DOT',','.join(x['dot_index'] for x in p)).replace('CHIP',','.join('0' if x['driver']=='A' else '1' for x in p))
cc=shutil.which('clang') or shutil.which('cc');assert cc
with tempfile.TemporaryDirectory(prefix='odradek-cd01-') as t:
 t=Path(t);(t/'mock.c').write_text(code)
 r=subprocess.run([cc,'-std=c99','-Wall','-Wextra','-Werror','-I',str(D),str(t/'mock.c'),str(D/'cd01_example.c'),'-o',str(t/'mock')],capture_output=True,text=True);assert r.returncode==0,r.stderr
 r=subprocess.run([str(t/'mock')],capture_output=True,text=True);assert r.returncode==0,r.stderr
out=dict(revision='CD-EC01',compiler=Path(cc).name,result='pass',hardware_execution=False,checks=['both explicit3mA initializations and all-black','142/143 fitted masks andDC','all285 unique little-endian PWM locations and absent zero','stage alone never pulses sharedVSYNC','both driver transport failures propagate withoutVSYNC','both driver readback corruption rejects init','all1024 read/write headers and invalid address rejection'],sha256={n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ['cd01_example.c','cd01_example.h','pixel-map.csv']})
(D/'firmware-check.json').write_text(json.dumps(out,indent=2)+'\n');print('CD01 C99 register mock passed')
