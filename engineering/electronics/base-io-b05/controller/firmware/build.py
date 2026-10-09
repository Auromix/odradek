# SPDX-License-Identifier: CC-BY-NC-4.0
"""Host tests, Cortex-M0+ build and independent ELF/vector/image checks.

Run with a Python environment containing ziglang==0.15.2 and host clang.
No hardware is flashed or qualified by this script.
"""
import hashlib,json,struct,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parent
def run(args):subprocess.run(args,cwd=R,check=True,timeout=30)
with tempfile.TemporaryDirectory(prefix='odradek-lamp-') as tmp:
    test=Path(tmp)/'effects-test'
    run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined,bounds','-g','effects.c','framing.c','test_effects.c','-o',str(test)])
    run([str(test)])
run([sys.executable,'-m','ziglang','cc','-target','thumb-freestanding-eabi','-mcpu=cortex_m0plus','-mthumb','-Os','-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-nostdlib','-Ivendor','-Wl,--script=linker.ld','-Wl,--entry=Reset_Handler','-Wl,--gc-sections','main.c','effects.c','framing.c','startup.S','-o','controller.elf'])
b=(R/'controller.elf').read_bytes();h=struct.unpack_from('<16sHHIIIIIHHHHHH',b)
assert h[0][:7]==b'\x7fELF\x01\x01\x01' and h[1]==2 and h[2]==40
entry=h[4];assert entry&1 and 0x08000000<=entry<0x08008000
loads=[];ram_max=0x20000000
for i in range(h[10]):
    p=struct.unpack_from('<8I',b,h[5]+i*h[9]);typ,offset,virt,phys,size,mem,flags,align=p
    if typ!=1:continue
    assert offset+size<=len(b) and mem>=size
    if 0x20000000<=virt<0x20002000:
        ram_max=max(ram_max,virt+mem);assert ram_max<=0x20002000-1024
    if size:
        assert 0x08000000<=phys and phys+size<=0x08008000
        loads.append((phys,b[offset:offset+size]))
assert loads and min(a for a,d in loads)==0x08000000
image=bytearray(b'\xff'*(max(a+len(d) for a,d in loads)-0x08000000))
used=set()
for a,d in loads:
    start=a-0x08000000;assert not any(i in used for i in range(start,start+len(d)))
    image[start:start+len(d)]=d;used.update(range(start,start+len(d)))
stack,reset=struct.unpack_from('<2I',image)
assert stack==0x20002000 and reset==entry
assert len(image)>192 and struct.unpack_from('<I',image,15*4)[0]&1
(R/'controller.bin').write_bytes(image)
def record(address,kind,data):
    v=bytes([len(data),address>>8,address&255,kind])+bytes(data)
    return ':'+(v+bytes([(-sum(v))&255])).hex().upper()
hex_lines=[record(0,4,[8,0])]+[record(i,0,image[i:i+16]) for i in range(0,len(image),16)]+[record(0,1,[])]
(R/'controller.hex').write_text('\n'.join(hex_lines)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[*R.glob('*.c'),*R.glob('*.h'),R/'startup.S',R/'linker.ld',R/'build.py',*sorted((R/'vendor').glob('*.h'))]
report={'date':'2026-10-09','host_tests_pass':True,'sanitizers':['undefined','bounds'],'cross_target':'thumb-freestanding-eabi cortex_m0plus','compiler':'ziglang 0.15.2','flash_origin':hex(0x08000000),'flash_bytes':len(image),'flash_budget_bytes':32768,'RAM_static_bytes':ram_max-0x20000000,'RAM_budget_bytes':8192,'stack_reserve_bytes':1024,'entry':hex(entry),'vector_stack':hex(stack),'reset_vector_matches_entry':True,'sources_sha256':{str(p.relative_to(R)):sha(p) for p in sources},'outputs_sha256':{p:sha(R/p) for p in ['controller.elf','controller.bin','controller.hex']},'limits':['No board connected or flashed','PWM, clocks, watchdog timing, UART electrical levels and SWD require physical tests','Programmed modes continue autonomously after UART disconnection; reset returns OFF; no stored mode'],'address_sanitizer_status':'Unavailable on this host: runtime initialization deadlocked before main; no ASan pass claimed','production_released':False}
(R/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('FIRMWARE_DIGITAL_PASS',len(image),'flash bytes;',ram_max-0x20000000,'static RAM bytes; physical=False')
