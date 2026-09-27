#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""HEAD-CTRL02 original circuit candidate. Builds native schematic, not a PCB."""
from pathlib import Path
import csv,json,math,uuid,hashlib,itertools
D=Path(__file__).resolve().parent; K=D/'kicad'; K.mkdir(exist_ok=True)
URL={
 'stm':'https://www.st.com/resource/en/datasheet/stm32g474ve.pdf',
 'lan':'https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/LAN9252-Data-Sheet-DS00001909.pdf',
 'lanref':'https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/BoardDesignFiles/lan9252-hbispigpio-evb-rev-b.pdf',
 'drv':'https://www.ti.com/lit/ds/symlink/drv8874.pdf','ref':'https://www.ti.com/lit/gpn/REF31',
 'mux':'https://www.ti.com/lit/ds/symlink/tmux1511.pdf','quad':'https://www.ti.com/lit/ds/symlink/sn74lvc08a.pdf',
 'and':'https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf','super':'https://www.ti.com/lit/ds/symlink/tps3808.pdf', 'resetbuf':'https://www.ti.com/lit/ds/symlink/sn74lvc2g07.pdf',
 'switch':'https://www.ti.com/lit/ds/symlink/tps22919.pdf','xtal':'https://abracon.com/Oscillators/ASTX-H12.pdf',
 'eeprom':'https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA512-24LC512-24FC512-512-Kbit-I2C-Serial-EEPROM-DS20001754.pdf',
 'gh':'https://www.jst-mfg.com/product/index.php?lang=2&series=105','vh':'https://www.jst-mfg.com/product/pdf/eng/eVH.pdf',
 'lp':'https://www.ti.com/lit/ds/symlink/lp5860.pdf','pulse':'https://www.pulseelectronics.com/wp-content/uploads/2020/12/Ethernet-Connector-Module-Selector-Guide-f.pdf'}
C=[];P=[];counts={};M=[]
def add(ref,value,mpn,pins,source='',fp='',group='',note='',status='candidate'):
 assert ref not in [c['ref'] for c in C]
 C.append(dict(ref=ref,value=value,mpn=mpn,footprint=fp,source_url=URL.get(source,source),group=group,selection_status=status,note=note))
 for num,name,net,role in pins:P.append(dict(ref=ref,pin=str(num),pin_name=name,net=net,electrical_role=role))
def passive(kind,value,a,b,group,note='',tol='',mpn='TBD'):
 counts[kind]=counts.get(kind,0)+1;ref=kind+str(counts[kind])
 fp={'R':'Resistor_SMD:R_0603_1608Metric','C':'Capacitor_SMD:C_0603_1608Metric','FB':'Inductor_SMD:L_0603_1608Metric','JP':'Jumper:Jumper_2_Open'}.get(kind,'')
 add(ref,value,mpn,[(1,'1',a,'passive'),(2,'2',b,'passive')],fp=fp,group=group,note=(tol+' '+note).strip())
 return ref
def R(v,a,b,g,n='',tol='1%'):return passive('R',v,a,b,g,n,tol)
def cap(v,a,g,n='',b='GND'):return passive('C',v,a,b,g,n)
def dec(net,g,qty=1,v='100nF 16V X7R'):
 for _ in range(qty):cap(v,net,g,'One directly at each indicated supply pin; final DC bias/MPN pending')
def output(name):return (name,name,'output')
# Exact LQFP100 pin order: ST DS12288 Rev6 Figure12 + Table12 pp56-72.
order=['PE2','PE3','PE4','PE5','PE6','VBAT','PC13','PC14','PC15','PF9','PF10','PF0','PF1','PG10_NRST','PC0','PC1','PC2','PC3','PF2','PA0','PA1','PA2','VSS','VDD','PA3','PA4','PA5','PA6','PA7','PC4','PC5','PB0','PB1','PB2','VSSA','VREF+','VDDA','PE7','PE8','PE9','PE10','PE11','PE12','PE13','PE14','PE15','PB10','VSS','VDD','PB11','PB12','PB13','PB14','PB15','PD8','PD9','PD10','PD11','PD12','PD13','PD14','PD15','VSS','VDD','PC6','PC7','PC8','PC9','PA8','PA9','PA10','PA11','PA12','VSS','VDD','PA13','PA14','PA15','PC10','PC11','PC12','PD0','PD1','PD2','PD3','PD4','PD5','PD6','PD7','PB3','PB4','PB5','PB6','PB7','PB8_BOOT0','PB9','PE0','PE1','VSS','VDD']
A={}
def assign(pin,net,role='output',periph='GPIO',af='',default='external pulldown; configure ODR=0 before output',note=''):
 assert pin not in A
 A[pin]=dict(net=net,role=role,peripheral=periph,af=af,reset_state=default,note=note)
for i,p in enumerate(['PE2','PE3','PE4','PE5','PE6','PC10']):assign(p,f'LED_CS{i}_MCU',default='external10k to switchedVIO; MCUhighZ untilVIOvalid, thenODR1 beforeoutput')
for prefix,ports in [('ESC',['PA5','PA6','PA7']),('LED',['PB13','PB14','PB15'])]:
 for p,sig,role in zip(ports,['SCK','MISO','MOSI'],['output','input','output']):assign(p,f'{prefix}_{sig}_MCU',role,'SPI1' if prefix=='ESC' else 'SPI2','AF5','low/high-Z until peer powered; 33ohm source damping candidate')
assign('PA4','ESC_CS_N','output','GPIO','','10k pullup to 3V3_LOGIC; high before SPI init')
for i in range(4):
 assign(f'PD{12+i}',f'M{i+1}_EN','output',f'TIM4_CH{i+1}','AF2','47k pulldown; timer disabled then CCR=0/ARR=799 at 16MHz before AF')
 assign(f'PD{8+i}',f'M{i+1}_PH')
 assign(f'PD{i}',f'M{i+1}_SLEEP_REQ')
 assign(f'PD{4+i}',f'M{i+1}_FAULT_N','input','GPIO polling','','10k pullup; poll; no EXTI6/7 conflict','Fast fault handling remains in DRV8874, polling is not a safety function')
 assign(f'PC{i}',f'M{i+1}_POT_ADC','input',f'ADC1_IN{6+i}','','analog/no pull','Pot exciter and VREF+ use the same 3V3_A; 1k/10nF filter')
 assign(f'PA{i}',f'M{i+1}_I_ADC','input',f'ADC1_IN{1+i}','','analog/no pull','100k divider + TMUX1511 + 100k discharge/10nF; RIPROPI 6.49k')
for p,ch,name in [('PE7',4,'NTC_P1'),('PE8',6,'NTC_P2'),('PE9',2,'NTC_P3'),('PE10',14,'NTC_P4'),('PE13',3,'NTC_C'),('PE11',15,'VM_ADC'),('PE12',16,'VLED_ADC')]:assign(p,name,'input',f'ADC3_IN{ch}','','analog/no pull','No duplicate NTC pullup; VM isolated through fifth TMUX channel')
assign('PC6','ESC_SYNC0','input','EXTI6','','input/no pull','TIM3_CH1 AF2 also legal but not selected; no simultaneous EXTI/timer claim')
assign('PC7','ESC_IRQ_N','input','EXTI7','','10k pullup; IRQ default open-drain active-low')
assign('PC8','ESC_SYNC1','input','EXTI8','','input/no pull')
assign('PC9','ESC_RESET_N','open_collector','GPIO open-drain + EXTI9','','external10kpullup; ODR1=>released; bootassertLow>=1ms withARM0','SeparatefromMCUNRST; fallrequireslatchedmotioninhibit beforefirmwareallowre-arm')
assign('PC11','LED_VSYNC_MCU')
assign('PC12','LED_IO_REQ')
assign('PE15','MCU_ARM')
assign('PB1','EXT_PERMIT','input','GPIO monitor','','47k external pulldown; ONLY 0/3.3V local interlock')
for p,n in zip(['PB2','PB10','PB11','PB12','PC13'],range(5)):assign(p,f'LED_PWR{n}_REQ',note='PC13 sources gate input only; no LED current')
assign('PA9','DEBUG_TX','output','USART1_TX','AF7','GPIO high-Z until UART init')
assign('PA10','DEBUG_RX','input','USART1_RX','AF7','10k pullup; do not backpower unpowered logic')
assign('PA13','SWDIO','bidirectional','SWD','AF0','reset debug function, internal pullup')
assign('PA14','SWCLK','input','SWD','AF0','reset debug function, internal pulldown')
assign('PB3','SWO','output','TRACE','AF0','optional SWO; no JTAG use')
assign('PB8_BOOT0','BOOT0','input','BOOT','','10k pulldown; open jumper to 3V3','Audit nSWBOOT0/nBOOT0 option bytes; not determined by wiring alone')
mp=[]
for n,p in enumerate(order,1):
 if p in ['VSS','VSSA']:net,role='GND','power_in';a={}
 elif p in ['VDD','VBAT']:net,role='3V3_LOGIC','power_in';a={}
 elif p in ['VDDA','VREF+']:net,role='3V3_A','power_in';a={}
 elif p=='PG10_NRST':net,role='MCU_RESET_N','open_collector';a={'peripheral':'NRST','reset_state':'Keepresetfunction; separateopen-drainsupervisorbuffer+debug, notshortedtoLAN'}
 elif p in A:a=A[p];net,role=a['net'],a['role']
 else:a={};net,role=None,'bidirectional'
 mp.append((n,p,net,role));M.append(dict(package_pin=n,pad_name=p,net=net or 'NC',direction=role,peripheral=a.get('peripheral','power' if role=='power_in' else 'unused'),alternate_function=a.get('af',''),default_state=a.get('reset_state','NC; firmware analog/no pull' if net is None else 'supply'),note=a.get('note',''),source=URL['stm'],table='DS12288 Rev6 Table12/13'))
add('U1','STM32G474VET6','STM32G474VET6',mp,'stm','Package_QFP:LQFP-100_14x14mm_P0.5mm','MCU','512k Flash/128k SRAM; HSI16 clock first-light, no HSE crystal fitted')
dec('3V3_LOGIC','MCU',5);cap('10uF 10V X7R','3V3_LOGIC','MCU');dec('3V3_LOGIC','MCU') # VBAT
passive('FB','220ohm@100MHz','3V3_LOGIC','3V3_A','MCU','Filter not galvanic isolation',mpn='BLM18EG221SN1D')
dec('3V3_A','MCU');cap('1uF 10V X7R','3V3_A','MCU');cap('100nF 16V X7R','3V3_A','MCU','At VREF+ pin36; internal VREFBUF disabled')
R('10k','BOOT0','GND','MCU');passive('JP','BOOT only while motors inhibited','BOOT0','3V3_LOGIC','MCU')
R('10k','DEBUG_RX','3V3_LOGIC','MCU')
# Source termination is separate per clock/MOSI path; MISO at LAN source.
for p in ['ESC_SCK','ESC_MOSI','LED_SCK','LED_MOSI','LED_VSYNC']:R('33',p+'_MCU',p,'MCU','Tune after real loom SI measurements')
R('33','ESC_MISO','ESC_MISO_MCU','ESC','At LAN SO source')
R('0','LED_MISO_BUS','LED_MISO_MCU','LED','Each FPL board already has its own 33ohm MISO resistor')
R('10k','ESC_CS_N','3V3_LOGIC','MCU')
# Reset and hardware inhibit, not certified STO.
add('U3','TPS3808G33DBVR','TPS3808G33DBVR',[(1,'RESET_N','SYS_RESET_N','open_collector'),(2,'GND','GND','power_in'),(3,'MR_N','RESET_BUTTON_N','input'),(4,'CT','RESET_CT','input'),(5,'SENSE','3V3_LOGIC','input'),(6,'VDD','3V3_LOGIC','power_in')],'super','Package_TO_SOT_SMD:SOT-23-6','RESET','CT via100k toVDD:180..420ms reset delay; exceeds LAN minimum25ms after rails valid if rails settle within150ms')
R('100k','RESET_CT','3V3_LOGIC','RESET');R('10k','SYS_RESET_N','3V3_LOGIC','RESET');R('10k','RESET_BUTTON_N','3V3_LOGIC','RESET');passive('JP','MANUAL_RESET','RESET_BUTTON_N','GND','RESET');dec('3V3_LOGIC','RESET')
def gate(ref,a,b,y):
 add(ref,'SN74LVC1G08DBVR','SN74LVC1G08DBVR',[(1,'A',a,'input'),(2,'B',b,'input'),(3,'GND','GND','power_in'),(4,'Y',y,'output'),(5,'VCC','3V3_LOGIC','power_in')],'and','Package_TO_SOT_SMD:SOT-23-5','INHIBIT');dec('3V3_LOGIC','INHIBIT')
gate('U4','MCU_ARM','EXT_PERMIT','ARM_PERMIT');gate('U5','ARM_PERMIT','SYS_RESET_N','MOTION_GATE_SYS');gate('U6','MOTION_GATE_SYS','ESC_RESET_N','MOTION_GATE');gate('U7','LED_IO_REQ','SYS_RESET_N','LED_IO_GATE')
for n in ['MCU_ARM','EXT_PERMIT','LED_IO_REQ']:R('47k',n,'GND','INHIBIT')
qp=[(7,'GND','GND','power_in'),(14,'VCC','3V3_LOGIC','power_in')]
for i,(a,b,y) in enumerate([(1,2,3),(4,5,6),(9,10,8),(12,13,11)],1):qp +=[(a,f'A{i}',f'M{i}_SLEEP_REQ','input'),(b,f'B{i}','MOTION_GATE','input'),(y,f'Y{i}',f'M{i}_SLEEP','output')]
add('U8','SN74LVC08APWR','SN74LVC08APWR',qp,'quad','Package_SO:TSSOP-14_4.4x5mm_P0.65mm','INHIBIT');dec('3V3_LOGIC','INHIBIT')
add('U23','SN74LVC2G07DCKR','SN74LVC2G07DCKR',[(1,'1A','SYS_RESET_N','input'),(2,'GND','GND','power_in'),(3,'2A','SYS_RESET_N','input'),(4,'2Y','ESC_RESET_N','open_collector'),(5,'VCC','3V3_LOGIC','power_in'),(6,'1Y','MCU_RESET_N','open_collector')],'resetbuf','Package_TO_SOT_SMD:SC-70-6','RESET','Twoindependentopen-drainresetbranches; MCUshortresetpulsedoesnotdisturbLAN. PC9canholdESCresetwithoutresettingitself.')
dec('3V3_LOGIC','RESET');R('10k','MCU_RESET_N','3V3_LOGIC','RESET');R('10k','ESC_RESET_N','3V3_LOGIC','RESET')
# LAN9252 SPI PDI, copper two-port mode. Package pinout is common to QFN/TQFP.
lnames=['OSCI','OSCO','OSCVDD12','OSCVSS','VDD33','VDDCR','REG_EN','FXLOSEN','FXSDENA','FXSDENB','RST_N','SIO2','SO_SIO1','VDDIO','GPIO8','GPIO7','SI_SIO0','SYNC1','SCK','VDDIO','GPIO6','GPIO5','GPIO4','VDDCR','MII_CLK25','GPIO11','GPIO12','GPIO13','GPIO10','GPIO14','GPIO15','VDDIO','GPIO9','SYNC0','SIO3','GPIO0','VDDIO','VDDCR','GPIO1','GPIO2','TESTMODE','EESDA','EESCL','IRQ','RUNLED_E2PSIZE','LINK1_CHIPMODE1','VDDIO','LINK0_CHIPMODE0','GPIO3','SCS_N','VDD33TXRX1','TXNA','TXPA','RXNA','RXPA','VDD12TX1','RBIAS','VDD33BIAS','VDD12TX2','RXPB','RXNB','TXPB','TXNB','VDD33TXRX2']
lmap={1:('OSC_25M','input'),3:(None,'power_out'),4:('GND','power_in'),5:('LAN_3V3','power_in'),6:('LAN_1V2','power_out'),7:('3V3_LOGIC','input'),8:('GND','input'),9:('GND','input'),10:('GND','input'),11:('ESC_RESET_N','open_collector'),12:('LAN_SIO2','input'),13:('ESC_MISO','tri_state'),17:('ESC_MOSI','input'),18:('ESC_SYNC1','output'),19:('ESC_SCK','input'),24:('LAN_1V2','power_in'),34:('ESC_SYNC0','output'),35:('LAN_SIO3','input'),38:('LAN_1V2','power_in'),41:('GND','input'),42:('EE_SDA','bidirectional'),43:('EE_SCL','output'),44:('ESC_IRQ_N','open_collector'),45:('LAN_E2PSIZE','open_collector'),46:('LAN_MODE1','open_emitter'),48:('LAN_MODE0','open_emitter'),50:('ESC_CS_N','input'),51:('PHY_3V3','power_in'),56:('PHY_1V2','power_in'),57:('RBIAS','passive'),58:('PHY_3V3','power_in'),59:('PHY_1V2','power_in'),64:('PHY_3V3','power_in')}
for n in [14,20,32,37,47]:lmap[n]=('3V3_LOGIC','power_in')
for n in [52,53,54,55,60,61,62,63]:lmap[n]=(lnames[n-1],'bidirectional')
add('U2','LAN9252I/PT','LAN9252I/PT',[(i,n,*lmap.get(i,(None,'bidirectional'))) for i,n in enumerate(lnames,1)]+[(65,'EP_VSS','GND','power_in')],'lan','HEAD:LAN9252_TQFP64_EP_candidate','ESC','Two-port copper. CHIP_MODE=00; SPI PDI=0x80 in SII, not set by CHIP_MODE straps. Footprint must be verified before PCB.')
for n,rail in [('LAN_E2PSIZE','3V3_LOGIC'),('LAN_MODE0','GND'),('LAN_MODE1','GND'),('LAN_SIO2','3V3_LOGIC'),('LAN_SIO3','3V3_LOGIC'),('ESC_IRQ_N','3V3_LOGIC')]:R('10k',n,rail,'ESC')
R('12.1k','RBIAS','GND','ESC','At pin57','1%')
for a,b in [('3V3_LOGIC','LAN_3V3'),('3V3_LOGIC','PHY_3V3'),('LAN_1V2','PHY_1V2')]:passive('FB','220ohm@100MHz',a,b,'ESC','Verify bead-current, ESR and power-sequence measurements',mpn='BLM18EG221SN1D')
dec('3V3_LOGIC','ESC',5);dec('LAN_3V3','ESC');cap('1uF 10V X7R','LAN_3V3','ESC');dec('PHY_3V3','ESC',3);cap('1uF 10V X7R','PHY_3V3','ESC');dec('PHY_1V2','ESC',2)
R('0.10','LAN_1V2','LAN_CORE_CAP','ESC','Series ESR provision for1uF at pin6; verify effective ESR per LAN DS4.1.1');cap('1uF 10V X7R','LAN_CORE_CAP','ESC','Effective ESR target0.1ohm requires regulator stability verification');cap('470pF 50V C0G','LAN_1V2','ESC','Parallel at pin6');dec('LAN_1V2','ESC',2)
add('Y1','25MHz HCMOS TCXO','ASTX-H12-25.000MHZ-T',[(1,'OE','3V3_LOGIC','input'),(2,'GND','GND','power_in'),(3,'OUT','OSC_SRC','output'),(4,'VDD','3V3_LOGIC','power_in')],'xtal','Oscillator:Oscillator_SMD_2.5x2.0mm','ESC','Catalogue ordering candidate; lifecycle/current quote unverified.0..70C board limit;3V3rail±3%.6ppm arithmetic budget through first year; measure loaded VOL<0.35V.')
R('33','OSC_SRC','OSC_25M','ESC','At oscillator source; no load capacitors; OSCO and OSCVDD12 leftNC per internal-regulator external-clock case');cap('10nF 16V X7R','3V3_LOGIC','ESC','At TCXO');dec('3V3_LOGIC','ESC')
add('U9','24FC512-I/SN','24FC512-I/SN',[(1,'A0','GND','input'),(2,'A1','GND','input'),(3,'A2','GND','input'),(4,'VSS','GND','power_in'),(5,'SDA','EE_SDA','bidirectional'),(6,'SCL','EE_SCL','input'),(7,'WP','EE_WP','input'),(8,'VCC','3V3_LOGIC','power_in')],'eeprom','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm','ESC','A0=0x50; WP high by default; fit service jumper only to program verified SII; ESI/vendor ID not yet issued')
for n in ['EE_SDA','EE_SCL','EE_WP']:R('4.7k' if n!='EE_WP' else '10k',n,'3V3_LOGIC','ESC')
passive('JP','EEPROM_WRITE_ENABLE','EE_WP','GND','ESC');dec('3V3_LOGIC','ESC')
# Magjack candidate from official EVB p5. Complete phy-side pin map; no copied vendor graphic.
for port in 'AB':
 p=[(1,'TD+','TXP'+port,'passive'),(2,'TD-','TXN'+port,'passive'),(3,'RD+','RXP'+port,'passive'),(4,'TXCT','PHY_3V3','passive'),(5,'RXCT','PHY_3V3','passive'),(6,'RD-','RXN'+port,'passive'),(7,'NC',None,'passive'),(8,'CHS_GND','CHASSIS','passive'),(9,'LED_A',None,'passive'),(10,'LED_K',None,'passive'),(11,'LED2_K',None,'passive'),(12,'LED2_A',None,'passive'),(13,'SHIELD','CHASSIS','passive'),(14,'SHIELD','CHASSIS','passive'),(15,'MECH',None,'passive'),(16,'MECH',None,'passive')]
 add('J_EC'+port,'100BASE-TX isolated magjack','J0011D01BNL',p,'lanref','HEAD:J0011D01BNL_candidate','ETHERNET','Bench connector only; board/plug/metal fit not proved. 0..70C catalog. No direct RH SH1.0 wiring assumption.')
 for net in ['TXP'+port,'TXN'+port,'RXP'+port,'RXN'+port]:R('49.9',net,'PHY_3V3','ETHERNET','Source EVB p5; 100ohm diff controlled pairs','1%')
 cap('22nF 50V X7R','PHY_3V3','ETHERNET','At magnetics CT')
R('0','CHASSIS','GND','ETHERNET','Bench-only bond link. EMC/PE/isolation scheme must be reviewed; not protective-earth conductor')
# Four independent DRV8874 bridges and feedback. Existing6.19k is deliberately replaced by6.49k here.
add('U10','2.5V reference','REF3125AIDBZR',[(1,'IN','3V3_A','power_in'),(2,'OUT','VREF_2V5','output'),(3,'GND','GND','power_in')],'ref','Package_TO_SOT_SMD:SOT-23','MOTOR','Local analog 2.5V; not MCU VREF+. Guarded startup before motor enable')
cap('100nF 16V X7R','3V3_A','MOTOR');cap('1uF 10V X7R','VREF_2V5','MOTOR','Verify REF31 output-cap ESR/load stability')
for i in range(1,5):
 g=f'MOTOR{i}';n=lambda s:f'M{i}_{s}'
 pin=[(1,'EN',n('EN'),'input'),(2,'PH',n('PH'),'input'),(3,'nSLEEP',n('SLEEP'),'input'),(4,'nFAULT',n('FAULT_N'),'open_collector'),(5,'VREF','VREF_2V5','input'),(6,'IPROPI',n('IPROPI'),'output'),(7,'IMODE',None,'input'),(8,'OUT1',n('OUT1'),'output'),(9,'PGND','GND','power_in'),(10,'OUT2',n('OUT2'),'output'),(11,'VM','VM_12V','power_in'),(12,'VCP',n('VCP'),'passive'),(13,'CPH',n('CPH'),'passive'),(14,'CPL',n('CPL'),'passive'),(15,'GND','GND','power_in'),(16,'PMODE','GND','input'),(17,'EP_GND','GND','power_in')]
 add(f'U{10+i}','DRV8874PWPR','DRV8874PWPR',pin,'drv','Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm','MOTOR'+str(i),'PMODE=0 PH/EN; IMODE intentionalHiZ selects fixed off-time + latched OCP. OUT2 is motor output, neverGND.')
 for sig in ['EN','PH','SLEEP_REQ','SLEEP']:R('47k',n(sig),'GND',g)
 R('10k',n('FAULT_N'),'3V3_LOGIC',g)
 cap('100nF 50V X7R','VM_12V',g,'AtVM');cap('22nF 50V X7R',n('CPH'),g,'Charge pump flying cap',b=n('CPL'));cap('100nF 16V X7R',n('VCP'),g,'BetweenVCP andVM; NOT toGND',b='VM_12V');cap('10uF 25V X7R','VM_12V',g,'Derated effective capacitance must be verified')
 R('6.49k',n('IPROPI'),'GND',g,'Threshold resistor; sensing-branch loading included in calculations.json','0.1%')
 R('100k',n('IPROPI'),n('I_DIV'),g,'Divider upper','0.1%');R('100k',n('I_DIV'),'GND',g,'Divider lower, even if TMUX off','0.1%');R('100k',n('I_ADC'),'GND',g,'Leakage discharge:2uA*100k=0.2V nominal','0.1%');cap('10nF 16V X7R',n('I_ADC'),g,'Filtered diagnostic only, ~0.5ms tau')
 R('1k',n('POT_W'),n('POT_ADC'),g,'ADCseries; 1Mohm wiper-open discharge is a calibrated load');R('1M',n('POT_ADC'),'GND',g,'Wiper-open decay to0; ~10msRC, not independent contact diagnosis');cap('10nF 16V X7R',n('POT_ADC'),g,'Pot contact noise; open-pot detection needs supervised excitation/test')
 add(f'J_M{i}','Motor pair, local board','B2P-VH(LF)(SN)',[(1,'OUT1',n('OUT1'),'passive'),(2,'OUT2',n('OUT2'),'passive')],'vh','Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical',g,'VHR-2N+SVH-21T-P1.1 candidate. Does not mate directly to unverified P16 OEM5pin housing; build keyed adapter harness after OEM pin1 verification')
 add(f'J_P{i}','Pot feedback, local board','BM03B-GHS-TBT(LF)(SN)',[(1,'POT_LOW','GND','passive'),(2,'POT_W',n('POT_W'),'passive'),(3,'POT_HIGH','3V3_A','passive')],'gh','Connector_JST:JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical',g,'GHR-03V-S+SSHL-002T-P0.2 candidate; prevent swap with power supply connectors')
# Isolation mux1 four current monitors; mux2 rail monitor plus3 grounded unused channels.
def mux(ref,channels):
 p=[(7,'GND','GND','power_in'),(14,'VDD','3V3_LOGIC','power_in')]
 for i,(sel,s,d) in enumerate([(1,2,3),(4,5,6),(10,9,8),(13,12,11)]):
  src,dst=channels[i];p.extend([(sel,'SEL'+str(i+1),'SYS_RESET_N' if src!='GND' else 'GND','input'),(s,'S'+str(i+1),src,'passive'),(d,'D'+str(i+1),dst,'passive')])
 add(ref,'TMUX1511PWR','TMUX1511PWR',p,'mux','Package_SO:TSSOP-14_4.4x5mm_P0.65mm','ADC','IPOFF max±2uA atVDD0; powered-off input0..3.6V; not surge-rated isolation');dec('3V3_LOGIC','ADC')
mux('U15',[(f'M{i}_I_DIV',f'M{i}_I_ADC') for i in range(1,5)])
R('100k','VM_12V','VM_DIV','ADC','VMdivider upper; VM must remain≤15V under all admitted bench operation','0.1%');R('20k','VM_DIV','GND','ADC','VMdivider lower','0.1%');R('100k','VM_ADC','GND','ADC','Leakage discharge','0.1%');cap('10nF 16V X7R','VM_ADC','ADC')
mux('U16',[('VM_DIV','VM_ADC'),('VLED_DIV','VLED_ADC'),('GND','GND'),('GND','GND')])
R('100k','3V3_LED','VLED_DIV','ADC','ADCdivider upper, isolated beforeMCU','0.1%');R('100k','VLED_DIV','GND','ADC','ADCdivider lower','0.1%');R('100k','VLED_ADC','GND','ADC','Powered-off leakage discharge','0.1%');cap('10nF 16V X7R','VLED_ADC','ADC')
# LED output rails: 4petals +central. VIO power is a switched supply, never MCU pin current.
def switch(ref,inp,out,enable,note):
 add(ref,'TPS22919DCKR','TPS22919DCKR',[(1,'IN',inp,'power_in'),(2,'GND','GND','power_in'),(3,'ON',enable,'input'),(4,'NC',None,'passive'),(5,'QOD',out,'passive'),(6,'VOUT',out,'power_out')],'switch','Package_TO_SOT_SMD:SC-70-6','LED',note);dec(inp,'LED');cap('1uF 10V X7R',out,'LED')
switch('U17','3V3_LOGIC','LED_VIO','LED_IO_GATE','CommonVIO enable; all bus outputs low/highZ beforedisable. QOD connected. MCU does not supply VIO current.')
for i in range(5):switch(f'U{18+i}','3V3_LED',f'LED_POWER{i}',f'LED_PWR{i}_REQ','Individual rail switch; self-protection is not coordinated 1A GH wire/fuse protection');R('47k',f'LED_PWR{i}_REQ','GND','LED')
for i in range(6):R('33',f'LED_CS{i}_MCU',f'LED_CS{i}','LED');R('10k',f'LED_CS{i}','LED_VIO','LED')
# Bus signal buffers/power-down protection are not fitted: software sequencing + no hotplug is a declared limitation.
for i in range(4):
 pins=[(1,'VLED',f'LED_POWER{i}','passive'),(2,'GND','GND','passive'),(3,'VCC','3V3_LOGIC','passive'),(4,'SCLK','LED_SCK','passive'),(5,'MOSI','LED_MOSI','passive'),(6,'MISO','LED_MISO_BUS','passive'),(7,'SS_N',f'LED_CS{i}','passive'),(8,'VSYNC','LED_VSYNC','passive'),(9,'VIO_EN','LED_VIO','passive'),(10,'NTC_RETURN',f'NTC_P{i+1}','passive')]
 add(f'J_L{i+1}','FPL01-compatible GH10','BM10B-GHS-TBT(LF)(SN)',pins,'gh','Connector_JST:JST_GH_BM10B-GHS-TBT_1x10-1MP_P1.25mm_Vertical','LED','MatingGHR-10V-S/SSHL-002T-P0.2; FPLhead pin10 already47k/1k/100nF; no duplicatepullup. Fullmatedheight/exitMCADpending')
cp=[(1,'VLED','LED_POWER4','passive'),(2,'GND','GND','passive'),(3,'VCC','3V3_LOGIC','passive'),(4,'SCLK','LED_SCK','passive'),(5,'MOSI','LED_MOSI','passive'),(6,'MISO','LED_MISO_BUS','passive'),(7,'CS_A','LED_CS4','passive'),(8,'VSYNC','LED_VSYNC','passive'),(9,'VIO_EN','LED_VIO','passive'),(10,'NTC_RETURN','NTC_C','passive'),(11,'CS_B','LED_CS5','passive'),(12,'GND','GND','passive')]
add('J_C','Central285LED/2LP5860','BM12B-GHS-TBT(LF)(SN)',cp,'gh','Connector_JST:JST_GH_BM12B-GHS-TBT_1x12-1MP_P1.25mm_Vertical','LED','CentralPCBA notyetdesigned; inputreturn mustreplicate47k+10kNTC+1k+100nF contract. MISOtri-stateverifieddevice; singleCS atatime.')
# Power/service boundaries. External supplies must be current-limited/conditioned.
add('J_VM','12V motor supply input','B6P-VH(LF)(SN)',[(1,'VM','VM_12V','passive'),(2,'GND','GND','passive')]+[(i,'NC',None,'passive') for i in range(3,7)],'vh','Connector_JST:JST_VH_B6P-VH_1x06_P3.96mm_Vertical','POWER','Sixpositions distinguishfrom2pinmotorports; VHR-6N candidate. Externalfuse/disconnect/regensink mandatorybeforemotoroperation; no onboardsurgeclampclaimed')
add('J_LOGIC','3.3V regulated logic input','B3P-VH(LF)(SN)',[(1,'3V3_LOGIC','3V3_LOGIC','passive'),(2,'GND','GND','passive'),(3,'NC',None,'passive')],'vh','Connector_JST:JST_VH_B3P-VH_1x03_P3.96mm_Vertical','POWER','External3.3V±3%,1Aplanning; no24V/5V directly. MatchingVHR-3Nandcrimpneeded; mechanicalmistake-proofingpending')
add('J_LED','3.3V regulated LED input','B4P-VH(LF)(SN)',[(1,'3V3_LED','3V3_LED','passive'),(2,'GND','GND','passive'),(3,'NC',None,'passive'),(4,'NC',None,'passive')],'vh','Connector_JST:JST_VH_B4P-VH_1x04_P3.96mm_Vertical','POWER','External3.3V±3%,3Aplanningseparatefromlogic; mustnotprecedelogic, nohotplug')
cap('1000uF 25V aluminium','VM_12V','POWER','Illustrativebulk, package/ESR/rippleMPNTBD;12→15V storesonly0.0405J, notregenapproval')
cap('22uF 10V X7R','3V3_LED','POWER','EffectiveDCbias/inrushpending');cap('22uF 10V X7R','3V3_LOGIC','POWER')
add('J_PERMIT','local 3.3V prototype interlock','BM02B-GHS-TBT(LF)(SN)',[(1,'PERMIT','EXT_PERMIT','passive'),(2,'GND','GND','passive')],'gh','Connector_JST:JST_GH_BM02B-GHS-TBT_1x02-1MP_P1.25mm_Vertical','INHIBIT','Not24Vinput,notSTO; externalcontactrequiresqualifiedlevelinterface; pulldowninhibitsonopen')
add('J_SWD','ARM Cortex SWD10','TBD keyed1.27mm',[(1,'VTREF','3V3_LOGIC','passive'),(2,'SWDIO','SWDIO','passive'),(3,'GND','GND','passive'),(4,'SWCLK','SWCLK','passive'),(5,'GND','GND','passive'),(6,'SWO','SWO','passive'),(7,'KEY',None,'passive'),(8,'NC',None,'passive'),(9,'GND','GND','passive'),(10,'nRESET','MCU_RESET_N','passive')],fp='Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical',group='MCU',note='VTREFsenseonly, do not power board from debug probe; wiring ARM10 standard, exactlockcandidateTBD')
add('J_UART','3.3V debug UART','BM04B-GHS-TBT(LF)(SN)',[(1,'VTREF','3V3_LOGIC','passive'),(2,'TX','DEBUG_TX','passive'),(3,'RX','DEBUG_RX','passive'),(4,'GND','GND','passive')],'gh','Connector_JST:JST_GH_BM04B-GHS-TBT_1x04-1MP_P1.25mm_Vertical','MCU','VTREFsenseonly; no RS232voltages; debugleadremovedbeforepoweroff')
# GH SMT hold-down pads are connected to GND; not cable conductors.
for c in C:
 if c['mpn'].startswith('BM') and '-GHS-' in c['mpn']:
  for n in ['M1','M2']:P.append(dict(ref=c['ref'],pin=n,pin_name='HOLD_DOWN',net='GND',electrical_role='passive'))
# Footprint candidates are metadata only; no assignedPCBfootprints at this schematic stage.
for c in C:
 if c['value'].startswith('1000uF'):c['footprint']='TBD aluminiumcase after ripple/ESR selection'
for c in C:
 c['qty']=1;c['unit_mass_g']='TBD';c['budget']='TBD; no procurement quote'
# Standard numeric connector references; functions remain explicit BOM metadata.
jcount=0
for c in C:
 old=c['ref'];c['functional_reference']=old
 if old.startswith('J_'):
  jcount+=1;c['ref']='J'+str(jcount)
  for pin in P:
   if pin['ref']==old:pin['ref']=c['ref']
# Explicit provenance and maturity for passive placeholders.
for c in C:
 if c['mpn']=='BLM18EG221SN1D':
  c['source_url']='https://www.murata.com/en-us/products/productdetail?partno=BLM18EG221SN1%23'
 elif c['mpn']=='TBD':
  c['selection_status']='TBD'
# Output authoritative tables.
def writecsv(path,rows):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
writecsv(D/'pinmux.csv',M);writecsv(D/'bom.csv',C);writecsv(D/'pin-net.csv',P)
(D/'netlist.json').write_text(json.dumps(dict(revision='HEAD-CTRL02',status='schematic engineering candidate; no board',components=C,pins=P),indent=2)+'\n')
# Calculate both switch states including resistor tolerances, not just unloadedRIPROPI.
def solve(rip=6490,rt=100000,rb=100000,rd=100000,ron=4.5):
 lower=1/(1/rb+1/(rd+ron));re=1/(1/rip+1/(rt+lower));k=lower/(rt+lower)*rd/(rd+ron)
 return re,k,2.5/(.00045*re)
req,k,it=solve();corners=[]
for signs in itertools.product([-1,1],repeat=6):
 rip,rt,rb,rd=[v*(1+s*.001) for v,s in zip([6490,100000,100000,100000],signs[:4])];re,kk,_=solve(rip,rt,rb,rd,4.5);corners.append(2.5*(1+signs[4]*.01)/(.00045*(1+signs[5]*.075)*re))
offreq=1/(1/6490+1/200000)
calc=dict(revision='HEAD-CTRL02',ipropi=dict(RIPROPI_ohm=6490,divider_top_ohm=100000,divider_bottom_ohm=100000,adc_discharge_ohm=100000,switch_Ron_bound_ohm=4.5,enabled_effective_R_ohm=req,enabled_ADC_ratio=k,enabled_Itrip_A=it,Itrip_corners_A=[min(corners),max(corners)],disabled_effective_R_ohm=offreq,disabled_Itrip_A=2.5/(.00045*offreq),input_stress_check_V=5.75,not_operating_setpoint=True,off_switch_input_max_V=5.75*1.001/(.999+1.001),on_ADC_max_V=5.75*k,ADC_poweroff_leakage_bound_V=2e-6*100000*1.001,filter_cap_F=10e-9,nominal_ADC_time_constant_s=(1/(1/100000+1/(4.5+1/(1/100000+1/(100000+6490)))))*10e-9,limitations=['DRV absmax5.75V is NOT a continuous operating target nor proof against arbitrary failure','TMUX IPoff bound specified VDD=0; supply-ramp/negative transient verification required','Current filter is diagnostic; native driverchopping/OCP independent','All resistorloads counted; priorP16CTRL01 6.19k baselineunchanged']),vm=dict(max_admitted_V=15,divider_top=100000,divider_bottom=20000,discharge=100000,enabled_ratio=1/7,off_ratio=1/6,off_source_max_V=2.5,bulk_nominal_F=.001,energy_12_to_15_J=.5*.001*(15**2-12**2)),lighting=dict(petal_baseline_W=2.264,central_baseline_VLED_A=.5182,power_input_peak_A=.28*2+.26*2+.52,first_light_mA_perLED=3,full20mA_requires_thermal_validation=True,all6_frame_bytes=2376,SPI2_Hz=2000000,payload_fraction_at60Hz=2376*8/2000000*60),reset=dict(supervisor_min_s=.180,LAN_after_all_rails_valid_min_s=.025,allowed_rail_and_clock_settling_after_logic_threshold_s=.155,requires_measurement=True),clock=dict(MCU_source='internalHSI16',MCU_Hz=16000000,TIM4_ARR=799,TIM4_PSC=0,PWM_Hz=20000,ESC_TCXO='ASTX-H12-25.000MHZ-T',catalogue_first_year_sum_ppm=6,overall_ETHERCAT_budget_ppm=25,actualclock_load_validation=False))
(D/'calculations.json').write_text(json.dumps(calc,indent=2)+'\n')
# Native symbol and schematic generation follows original pin facts, not a vendor artwork copy.
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/Auromix/odradek/HEAD-CTRL02/'+s))
def q(s):return json.dumps(str(s))
def f(v):return f'{float(v):.5f}'.rstrip('0').rstrip('.') if v else '0'
def eff(sz=1,j=''):return f'(effects (font (size {sz} {sz}))'+(f' (justify {j})' if j else '')+')'
def prop(k,v,x,y,hide=False):return f'(property {q(k)} {q(v)} (at {f(x)} {f(y)} 0) (effects (font (size 1 1))'+(' hide' if hide else '')+'))'
ROOT=uid('root');lib=[];placed=[];wires=[];byref={c['ref']:c for c in C};pinmap={r:[p for p in P if p['ref']==r] for r in byref};bbox=[]
def sym(c,px,py):
 px=round(px/1.27)*1.27;py=round(py/1.27)*1.27;ref=c['ref'];pins=pinmap[ref];N=len(pins);small=N==2 and ref.startswith(('R','C','FB','JP'))
 nh=(N+1)//2;hw=22.86 if N>30 else 15.24 if N>10 else 10.16;top=max(5.08,nh*2.54/2);loc=[]
 if small:top=2.54;hw=2.54;loc=[(pins[0],-5.08,0,0),(pins[1],5.08,0,180)]
 else:
  for i,p in enumerate(pins):
   left=i<nh;j=i if left else i-nh;loc.append((p,-hw-2.54 if left else hw+2.54,((nh-1)/2-j)*2.54,0 if left else 180))
 name=ref;lid='HEAD:'+ref
 graphic=f'(rectangle (start {-hw} {top}) (end {hw} {-top}) (stroke (width .254) (type default)) (fill (type background)))'
 if small and ref.startswith('C'):
  graphic='(polyline (pts (xy -.635 -1.27) (xy -.635 1.27)) (stroke (width .254) (type default)) (fill (type none))) (polyline (pts (xy .635 -1.27) (xy .635 1.27)) (stroke (width .254) (type default)) (fill (type none)))'
 block=[f'(symbol {q(lid)} (pin_names (offset 1.016)'+(' hide' if small else '')+')'+(' (pin_numbers hide)' if small else '')+' (in_bom yes) (on_board yes)',prop('Reference',ref,0,top+3),prop('Value',c['value'],0,-top-3),f'(symbol {q(name+"_0_1")} {graphic})',f'(symbol {q(name+"_1_1")}']
 for p,x,y,ang in loc:block.append(f'(pin {p["electrical_role"]} line (at {f(x)} {f(y)} {ang}) (length {4.445 if small and ref.startswith("C") else 2.54}) (name {q(p["pin_name"])} {eff(.85)}) (number {q(p["pin"])} {eff(.85)}))')
 block.extend([')',')']);lib.append((lid,'\n'.join(block)));sid=uid(ref)
 inst=[f'(symbol (lib_id {q(lid)}) (at {f(px)} {f(py)} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sid})',prop('Reference',ref,px,py-top-4),prop('Value',c['value'],px,py-top-2.2),prop('Footprint','',px,py,True),prop('CandidateFootprint',c['footprint'],px,py,True),prop('Datasheet',c['source_url'],px,py,True),prop('MPN',c['mpn'],px,py,True)]
 for p,lx,ly,ang in loc:
  inst.append(f'(pin {q(p["pin"])} (uuid {uid(ref+"pin"+p["pin"])}))');x=px+lx;y=py-ly
  if p['net'] is None:wires.append(f'(no_connect (at {f(x)} {f(y)}) (uuid {uid("nc"+ref+p["pin"])}))');continue
  ex=x+(-20.32 if ang==0 else 20.32)
  wires.append(f'(wire (pts (xy {f(x)} {f(y)}) (xy {f(ex)} {f(y)})) (stroke (width .1524) (type default)) (uuid {uid("w"+ref+p["pin"])}))')
  wires.append(f'(global_label {q(p["net"])} (shape bidirectional) (at {f(ex)} {f(y)} {180 if ang==0 else 0}) {eff(.85,"right" if ang==0 else "left")} (uuid {uid("l"+ref+p["pin"])}))')
 inst.append(f'(instances (project "head" (path {q("/"+ROOT)} (reference {q(ref)}) (unit 1))))');inst.append(')');placed.append('\n'.join(inst));bbox.append(dict(ref=ref,center_mm=[px,py],symbol_bbox=[px-hw,py-top,px+hw,py+top]))
# Large functional devices top half; small parts grouped by function below.
special={'U1':(110,118),'U2':(320,96),'U23':(520,165),'U3':(520,55),'U4':(680,55),'U5':(840,55),'U6':(1000,55),'U7':(520,110),'U8':(680,110),'U9':(840,110),'U10':(1000,110),'U11':(110,242),'U12':(320,242),'U13':(520,242),'U14':(730,242),'U15':(920,242),'U16':(1090,242),'U17':(110,306),'U18':(290,306),'U19':(470,306),'U20':(650,306),'U21':(830,306),'U22':(1010,306),'Y1':(320,165)}
for ref,pos in special.items():sym(byref[ref],*pos)
conn=[c for c in C if (c['ref'].startswith('J') and not c['ref'].startswith('JP'))]
for i,c in enumerate(conn):sym(c,85+(i%7)*165,376+(i//7)*64)
rest=[c for c in C if c['ref'] not in special and not (c['ref'].startswith('J') and not c['ref'].startswith('JP'))]
slots=[]
for rr in range(20):
 for cc in range(14):
  x=52+cc*78;y=585+rr*14
  if y>766 and x>940:continue
  slots.append((x,y))
for c,pos in zip(rest,slots):sym(c,*pos)
# Explicit flags mark only externally supplied rails or power transferred through passives.
flags=['GND','3V3_LOGIC','3V3_LED','VM_12V','3V3_A','LAN_3V3','PHY_3V3','PHY_1V2']
flag='HEAD:PWR_FLAG';lib.append((flag,'(symbol "HEAD:PWR_FLAG" (power) (pin_names (offset 0)) (in_bom no) (on_board no) '+prop('Reference','#FLG',0,2,True)+prop('Value','PWR_FLAG',0,-2,True)+' (symbol "PWR_FLAG_0_1" (polyline (pts (xy -1 1) (xy 0 2) (xy 1 1) (xy 0 0) (xy -1 1)) (stroke (width .254) (type default)) (fill (type none)))) (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'))
for i,net in enumerate(flags):
 ref=f'#FLG0{i+1}';x=round((40+i*110)/1.27)*1.27;y=round(555/1.27)*1.27
 placed.append(f'(symbol (lib_id {q(flag)}) (at {f(x)} {f(y)} 0) (unit 1) (in_bom no) (on_board no) (uuid {uid(ref)}) {prop("Reference",ref,x,y,True)} {prop("Value","PWR_FLAG",x,y,True)} (pin "1" (uuid {uid(ref+"pin")})) (instances (project "head" (path {q("/"+ROOT)} (reference {q(ref)}) (unit 1)))))');wires.append(f'(global_label {q(net)} (shape bidirectional) (at {f(x)} {f(y)} 0) {eff(.85,"left")} (uuid {uid("flag"+net)}))')
def txt(t,x,y,s=1.8):return f'(text {q(t)} (at {x} {y} 0) {eff(s,"left")} (uuid {uid(t)}))'
texts=[txt('HEAD-CTRL02 / 7 RH arm slaves + 1 head EtherCAT slave / P16 DC branch only',20,15,3),txt('SCHEMATIC CANDIDATE. No PCB. No safety, thermal, regeneration, manufacturing or 2kg-grasp release.',20,24,2),txt('Motor outputs OUT1/OUT2 are a floating H-bridge pair. RH B brakes use RH DC input; RH14 N has no brake.',20,33),txt('MCU/ESC and interlocks',20,44),txt('Four independent PH/EN motor channels and powered-off current-monitor isolation',20,205),txt('LED VIO + five VLED switches; SPI6 CS / 5 temperatures',20,278),txt('Connectors: full mating envelopes NOT fitted in MCAD; magjacks are bench candidates',20,341),txt('Power flags denote external supply or passive-filter transfer; they are not protection devices.',20,543),txt('Passive parts: identities and net labels are authoritative; one-decoupler-per-pin layout remains a PCB obligation.',20,572)]
content=['(kicad_sch (version 20231120) (generator "odradek_head_ctrl02")',f'(uuid {ROOT}) (paper "A0")','(title_block (title "HEAD-CTRL02 pin-level circuit candidate") (date "2026-09-27") (rev "HEAD-CTRL02") (company "Auromix contributors / CC-BY-NC-4.0") (comment 1 "ERC proves connectivity classes only; PCB/MCAD/safety/regen and SII firmware pending"))','(lib_symbols',*[v[1] for v in lib],')',*texts,*wires,*placed,'(sheet_instances (path "/" (page "1")))',')']
(K/'head.kicad_sch').write_text('\n'.join(content)+'\n');(K/'HEAD.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "odradek_head_ctrl02")\n'+'\n'.join(v[1].replace('"HEAD:','"',1) for v in lib)+'\n)\n');(K/'sym-lib-table').write_text('(sym_lib_table (lib (name "HEAD") (type "KiCad") (uri "${KIPRJMOD}/HEAD.kicad_sym") (options "") (descr "Original HEAD-CTRL02 pin facts")))\n');(K/'head.kicad_pro').write_text(json.dumps({'meta':{'filename':'head.kicad_pro','version':1}},indent=2)+'\n');(K/'schematic-placement.json').write_text(json.dumps(bbox,indent=2)+'\n')
print(json.dumps({'components':len(C),'pins':len(P),'MCUpins':len(M),'minmaxItrip':calc['ipropi']['Itrip_corners_A'],'small_rows':math.ceil(len(rest)/12),'maxY':max(x['symbol_bbox'][3] for x in bbox)}))
