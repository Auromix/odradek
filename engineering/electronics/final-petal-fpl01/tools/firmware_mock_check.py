# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Exercise generated host callbacks; not electrical/SPI hardware validation."""
import csv,json,shutil,subprocess,tempfile,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent.parent;clang=shutil.which('clang')
if not clang:raise SystemExit('clang is required for this mock transport check')
results={}
for kind in ['upper','lower']:
 p=D/kind;name='fpl01_'+kind;rows=list(csv.DictReader((p/'led-placement-reference.csv').open()));count=len(rows)
 expect=','.join(r['dot_index'] for r in rows)
 code='''#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "NAME_example.h"
static uint8_t reg[1024]; static int fail;
static int wr(uint16_t a,const uint8_t*p,size_t n){if(fail)return -1;assert(a+n<=1024);memcpy(reg+a,p,n);return 0;}
static int rd(uint16_t a,uint8_t*p,size_t n){assert(a+n<=1024);memcpy(p,reg+a,n);return 0;}
static void sync(int x){assert(x==0||x==1);}static void wait_us(uint32_t n){assert(n>=100);}
int main(void){NAME_io io={wr,rd,sync,wait_us};uint16_t pixels[COUNT];unsigned map[COUNT]={EXPECT};
memset(reg,0xA5,sizeof reg);assert(NAME_init_dark(&io)==0);assert(reg[0]==1&&reg[4]==0x51&&reg[5]==0);
for(unsigned i=0;i<396;i++)assert(reg[0x200+i]==0);
unsigned on=0;for(unsigned d=0;d<198;d++){unsigned row=d/18,cs=d%18;unsigned bit=(reg[0x43+3*row+cs/8]>>(cs%8))&1;on+=bit;assert(reg[0x100+d]==(bit?255:0));}assert(on==COUNT);
for(unsigned i=0;i<COUNT;i++)pixels[i]=(uint16_t)(0x1234+i);
assert(NAME_frame(&io,pixels,9)==0);assert(reg[4]==0x51&&reg[5]==9);
unsigned fitted[198]={0};for(unsigned i=0;i<COUNT;i++){assert(map[i]<198&&!fitted[map[i]]);fitted[map[i]]=1;assert(reg[0x200+2*map[i]]==(uint8_t)pixels[i]);assert(reg[0x201+2*map[i]]==(uint8_t)(pixels[i]>>8));}
for(unsigned i=0;i<198;i++)if(!fitted[i])assert(reg[0x200+2*i]==0&&reg[0x201+2*i]==0);
for(unsigned a=0;a<1024;a++){uint8_t h[2];NAME_spi_header(a,1,h);assert(h[0]==a/4&&h[1]==((a%4)*64+32));NAME_spi_header(a,0,h);assert(h[0]==a/4&&h[1]==(a%4)*64);}
fail=1;assert(NAME_frame(&io,pixels,9)<0);assert(NAME_init_dark(&io)<0);return 0;}
'''.replace('NAME',name).replace('COUNT',str(count)).replace('EXPECT',expect)
 with tempfile.TemporaryDirectory(prefix='odradek-fpl01-') as temp:
  t=Path(temp);(t/'test.c').write_text(code)
  c=subprocess.run([clang,'-std=c99','-Wall','-Wextra','-Werror','-I',str(p),str(t/'test.c'),str(p/(name+'_example.c')),'-o',str(t/'test')],capture_output=True,text=True);assert c.returncode==0,c.stderr
  r=subprocess.run([str(t/'test')],capture_output=True,text=True);assert r.returncode==0,r.stderr
 results[kind]={'LED_count':count,'passed':True,'checks':['dark initialization and explicit 3mA register','ON/OFF and DC masks agree','16bit LE PWM maps fitted pixels and leaves absent sites zero','all 1024 SPI address headers','callback failures propagate'],'source_sha256':hashlib.sha256((p/(name+'_example.c')).read_bytes()).hexdigest(),'map_sha256':hashlib.sha256((p/'led-placement-reference.csv').read_bytes()).hexdigest()}
(D/'firmware-mock-check.json').write_text(json.dumps({'status':'compiled C99 with in-memory transport mock, not executed on LED driver hardware','results':results,'hardware_execution':False},indent=2)+'\n');print('Both panel C99 mock transport checks passed')
