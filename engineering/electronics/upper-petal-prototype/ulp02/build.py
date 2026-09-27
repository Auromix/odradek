# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Build a tool-neutral circuit review package, NOT a routed PCB or Gerber.

The source pixel coordinates are immutable; the physical-adjacency SW/CS map is ULP-02. This
script creates every component/pin connection, initialization bytes and drawings.
"""
import csv
import hashlib
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PIXEL_SOURCE = ROOT/'docs/engineering/sources/head-lighting-io.json'
DS = 'https://www.ti.com/lit/ds/symlink/lp5860.pdf'
TRM = 'https://www.ti.com/lit/pdf/SNVU786'
EVM = 'https://www.ti.com/lit/pdf/SNVU762'
LED = 'https://www.we-online.com/components/products/datasheet/150060YS75000.pdf'
GH = 'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf'
RES = 'https://www.vishay.com/docs/20035/dcrcwe3.pdf'
NTC = 'https://www.murata.com/-/media/webrenewal/products/thermistor/ntc/ncu/ncu18-s.ashx?cvid=20240402040000000000&la=en-us'
TDK = 'https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no='


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, data): (OUT/name).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
def csvwrite(name, rows):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def spi_header(address, write=True):
    assert 0 <= address < 1024
    return [address >> 2, ((address & 3) << 6) | (0x20 if write else 0)]


def svg_start(w, h, title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
      '<style>text{font-family:Arial,sans-serif;fill:#163443} .wire{stroke:#276979;fill:none;stroke-width:1.5} .box{fill:#f1f6f8;stroke:#163443;stroke-width:1.5}</style>',
      f'<rect width="{w}" height="{h}" fill="white"/>',
      f'<text x="30" y="38" font-size="25" font-weight="bold">{title}</text>',
      f'<text x="30" y="64" font-size="14">{subtitle}</text>']


def text(s, x, y, label, size=13):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}">{html.escape(str(label))}</text>')


def line(s, x1, y1, x2, y2):
    s.append(f'<line class="wire" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')


def draw_schematic(components, pins):
    s = svg_start(1500, 1350, 'UPPER PETAL / COMPONENT CIRCUIT - ULP-02',
                  'HLIO-R03 electrical coupon. Repeated LEDs are on matrix sheet. Tool-neutral drawing; native KiCad checks are separate. No fabrication release.')
    byref = {c['ref']: c for c in components}
    s.append('<rect class="box" x="420" y="125" width="590" height="500"/>')
    text(s, 585, 112, 'U1  LP5860RKPR  RKP0040B', 18)
    upins = [p for p in pins if p['ref']=='U1']
    for i, p in enumerate(upins):
        y = 153+(i%21)*22
        if i < 21:
            text(s, 435, y, f'{p["pin"]}  {p["pin_name"]}', 12)
            line(s, 380, y-4, 420, y-4); text(s, 225, y, p['net'] or 'NC - FLOAT', 12)
        else:
            text(s, 830, y, f'{p["pin"]}  {p["pin_name"]}', 12)
            line(s, 1010, y-4, 1050, y-4); text(s, 1056, y, p['net'] or 'NC - FLOAT', 12)
    text(s, 30, 660, 'J1 / 10-way GH - electrical numbers; view/mirror per manufacturer drawing', 17)
    for i,p in enumerate(p for p in pins if p['ref']=='J1'):
        text(s, 40+(i//6)*330, 689+(i%6)*22, f'{p["pin"]}: {p["net"]}', 13)
    text(s, 725, 660, 'VIO_EN: supply AND enable; all bus pins must follow its rail.', 16)
    text(s, 725, 686, 'Do not power off VIO_EN while host or another MISO device drives high.', 13)
    text(s, 725, 710, 'This candidate uses one point-to-point SPI bus on the bench.', 13)
    text(s, 30, 835, 'ALL LOCAL PASSIVES / each line is a complete two-terminal net connection', 18)
    passive = [c for c in components if c['ref'].startswith(('C','R','TH'))]
    for i,c in enumerate(passive):
        col = i//10; row=i%10; x=30+col*740; y=871+row*37
        cp=[p for p in pins if p['ref']==c['ref']]
        label = 'TH1  NTC 10k 1%' if c['ref']=='TH1' else c['ref']+' '+c['value']
        text(s, x, y, label, 13)
        text(s, x+139, y, cp[0]['net'], 12); line(s,x+295,y-4,x+325,y-4)
        if c['ref'].startswith('C'):
            line(s,x+325,y-13,x+325,y+5);line(s,x+333,y-13,x+333,y+5);line(s,x+333,y-4,x+365,y-4)
        else:
            s.append(f'<rect class="box" x="{x+325}" y="{y-11}" width="40" height="14"/>')
        line(s,x+365,y-4,x+390,y-4);text(s,x+397,y,cp[1]['net'],12)
    text(s,30,1272,'No external ISET resistor: current is set by MC, CC and DC registers. No per-LED ballast is populated.',14)
    text(s,30,1298,'AGND + exposed pad 41 connect to GND copper. VCAP is decoupled only; never feed it from 3.3 V.',14)
    text(s,30,1328,'CC-BY-NC-4.0 | Auromix contributors | Pin-level CSV/JSON are the exhaustive electrical reference.',12)
    s.append('</svg>'); (OUT/'schematic-control.svg').write_text('\n'.join(s))


def draw_matrix(pixels):
    s=svg_start(2100, 1340, 'UPPER PETAL / 113 DISCRETE LED CONNECTIONS',
                'Each cell has named SW anode and CS cathode nets; no connection is implied between adjacent cells.')
    mapping={(p['sw'],p['cs']):p for p in pixels}
    text(s,30,92,'D pin 2 = A (+); D pin 1 = K (-), polarity mark. SW = high-side source; CS = current sink.',15)
    for cs in range(14): text(s,90+cs*143,125,f'CS{cs}',14)
    for sw in range(11):
        text(s,20,180+sw*102,f'SW{sw}',14)
        for cs in range(14):
            x=85+cs*143;y=175+sw*102;p=mapping.get((sw,cs))
            if not p:
                text(s,x,y,'NOT FITTED',10);continue
            text(s,x,y-17,p['ref'],12)
            line(s,x,y,x+26,y)
            s.append(f'<path class="wire" d="M {x+26},{y-8} L {x+26},{y+8} L {x+43},{y} Z"/>')
            line(s,x+44,y-9,x+44,y+9);line(s,x+44,y,x+72,y)
            text(s,x,y+20,f'2/A:SW{sw}',10);text(s,x,y+36,f'1/K:CS{cs}',10)
            text(s,x,y+52,f'XY {p["x_mm"]},{p["y_mm"]} mm',10)
    text(s,30,1310,'Unused sites are explicitly OFF in the register masks. U1 CS14...CS17 are floating pins.',14)
    s.append('</svg>');(OUT/'schematic-led-matrix.svg').write_text('\n'.join(s))


def main():
    data=json.loads(PIXEL_SOURCE.read_text());panel=next(p for p in data['pixel_maps'] if p['panel']=='UR')
    pixels=[dict(p,ref=f'D{i}') for i,p in enumerate(panel['drivers'][0]['pixels'],1)]
    xs=sorted({p['x_mm'] for p in pixels});ys=sorted({p['y_mm'] for p in pixels})
    oldmap=[dict(p) for p in pixels]
    for p in pixels:
        ix=xs.index(p['x_mm']);iy=ys.index(p['y_mm']);p.update(sw=ix//2,cs=iy+7*(ix%2))
    save('mapping-revision.json',{'revision':'ULP-02','coordinates_unchanged':True,'formula':'SW=floor(x-column-index/2); CS=y-row-index+7*(x-column-index modulo 2)','x_columns_mm':xs,'y_rows_mm':ys,'previous_ULP01_map':oldmap,'new_map':pixels})
    assert len(pixels)==113 and len({(p['sw'],p['cs']) for p in pixels})==113
    components=[];pins=[]
    def component(ref,mpn,value,footprint,source,side='B',xy=None,note=''):
        components.append({'ref':ref,'quantity':1,'manufacturer_part_number':mpn,'value':value,'footprint':footprint,
            'side':side,'x_mm':xy[0] if xy else '', 'y_mm':xy[1] if xy else '',
            'selection_status':'circuit-prototype-candidate','source_url':source,'notes':note})
    def pin(ref,num,name,net,role='passive'):pins.append({'ref':ref,'pin':str(num),'pin_name':name,'net':net,'electrical_role':role})
    component('U1','LP5860RKPR','11x18 driver','TI_RKP0040B',DS,xy=(43,0))
    names={**{i+1:f'CS{i}' for i in range(9)},**{10+i:f'SW{i}' for i in range(6)},16:'VLED',
        **{17+i:f'SW{i+6}' for i in range(5)},**{22+i:f'CS{i+9}' for i in range(9)},
        31:'AGND',32:'VCAP',33:'IFS',34:'VSYNC',35:'SCL_SCLK',36:'SDA_MOSI',37:'ADDR0_MISO',38:'ADDR1_SS',39:'VIO_EN',40:'VCC',41:'EP_GND'}
    special={'AGND':'GND','EP_GND':'GND','VCAP':'VCAP','IFS':'IFS','VSYNC':'VSYNC','SCL_SCLK':'SCLK','SDA_MOSI':'MOSI',
             'ADDR0_MISO':'MISO_IC','ADDR1_SS':'SS_N','VIO_EN':'VIO_EN','VCC':'VCC_3V3','VLED':'VLED_3V3'}
    for num,name in sorted(names.items()):
        net=name if name.startswith(('CS','SW')) else special[name]
        if name.startswith('CS') and int(name[2:])>13: net=None
        role='power_in' if name in ['VCC','VLED','VIO_EN','AGND','EP_GND'] else ('output' if name.startswith(('CS','SW')) or name in ['VCAP','ADDR0_MISO'] else 'input')
        pin('U1',num,name,net,role)
    for p in pixels:
        component(p['ref'],'150060YS75000','Yellow 590nm','WE_150060YS75000',LED,'F',(p['x_mm'],p['y_mm']),f'SW{p["sw"]}/CS{p["cs"]}; physical-adjacency ULP-02 mapping; HLIO-R03 XY unchanged')
        pin(p['ref'],1,'K',f'CS{p["cs"]}');pin(p['ref'],2,'A',f'SW{p["sw"]}')
    jnets=['VLED_3V3','GND','VCC_3V3','SCLK','MOSI','MISO_HOST','SS_N','VSYNC','VIO_EN','NTC_RETURN']
    component('J1','BM10B-GHS-TBT(LF)(SN)','10pin GH top-entry','JST_GH_10_TOP',GH,xy=(24,0),note='Backside; candidate rotation 90 deg; mated height 7.3 mm excludes wire bend')
    for i,n in enumerate(jnets,1):pin('J1',i,n,n)
    for n in ['M1','M2']:pin('J1',n,'solder_hold_down','GND')
    caps=[('C1','C2012X5R1V226M125AC','22uF 35V X5R','C0805','VLED_3V3',(33,8)),
          ('C2','C2012X5R1V226M125AC','22uF 35V X5R','C0805','VLED_3V3',(33,11)),
          ('C3','C1608X7R1E105K080AB','1uF 25V X7R','C0603','VLED_3V3',(42,4)),
          ('C4','C1608X7R1E105K080AB','1uF 25V X7R','C0603','VCC_3V3',(41,-4)),
          ('C5','C1608X7R1E105K080AB','1uF 25V X7R','C0603','VCAP',(47,-1)),
          ('C6','C1608X7R1H104K080AA','100nF 50V X7R','C0603','VLED_3V3',(45,4)),
          ('C7','C1608X7R1H104K080AA','100nF 50V X7R','C0603','VCC_3V3',(44,-4)),
          ('C8','C1608C0G1H102J080AA','1nF 50V C0G','C0603','VIO_EN',(47,-4)),
          ('C9','C1608X7R1H104K080AA','100nF 50V X7R','C0603','NTC_RETURN',(78,-4))]
    for ref,mpn,value,fp,net,xy in caps:
        component(ref,mpn,value,fp,TDK+mpn,xy=xy);pin(ref,1,'1',net);pin(ref,2,'2','GND')
    rs=[('R1','4K70','4.7k','VIO_EN','IFS',(51,4)),('R2','10K0','10k','VIO_EN','SS_N',(55,4)),
        ('R3','100K','100k','VIO_EN','GND',(59,4)),('R4','100K','100k','SCLK','GND',(51,0)),
        ('R5','100K','100k','MOSI','GND',(55,0)),('R6','100K','100k','VSYNC','GND',(59,0)),
        ('R7','33R0','33R','MISO_IC','MISO_HOST',(51,-4)),('R8','47K0','47k','VCC_3V3','NTC_NODE',(73,-4)),
        ('R9','1K00','1k','NTC_NODE','NTC_RETURN',(76,-4))]
    for ref,code,value,a,b,xy in rs:
        component(ref,'CRCW0603'+code+'FKEA',value+' 1%','R0603',RES,xy=xy);pin(ref,1,'1',a);pin(ref,2,'2',b)
    component('TH1','NCU18XH103F6SRB','NTC 10k 1% B25/50=3380K','NTC0603',NTC,xy=(76,0),note='Replaces NRND NCP18; body 1.6x0.8x0.8 mm +/-0.15, 47k bias; use controlled R-T data for firmware; no junction-temperature claim')
    pin('TH1',1,'1','NTC_NODE');pin('TH1',2,'2','GND')
    nets=defaultdict(list)
    for p in pins:
        if p['net']:nets[p['net']].append({'ref':p['ref'],'pin':p['pin']})
    assert len({(p['ref'],p['pin']) for p in pins})==len(pins)
    assert set(p['ref'] for p in pins)==set(c['ref'] for c in components)
    assert all(len(n)>1 for n in nets.values())
    assert len([p for p in pins if p['net'] is None])==4
    for p in pixels:
        lp=[n for n in pins if n['ref']==p['ref']]
        assert lp[0]['pin']=='1' and lp[0]['net']==f'CS{p["cs"]}'
        assert lp[1]['pin']=='2' and lp[1]['net']==f'SW{p["sw"]}'
    csvwrite('bom.csv',components);csvwrite('pin-net.csv',pins)
    csvwrite('external-interface-bom.csv',[
        {'item':'Cable housing','quantity':1,'manufacturer_part_number':'GHR-10V-S','source_url':GH,'status':'candidate','notes':'one petal-side housing; host end is bench-specific'},
        {'item':'Crimp contacts','quantity':10,'manufacturer_part_number':'SSHL-002T-P0.2','source_url':GH,'status':'candidate','notes':'correct crimp tooling/height and pull test required; no hand-solder substitution into crimp barrel'},
        {'item':'Host source terminations','quantity':3,'manufacturer_part_number':'CRCW060333R0FKEA','source_url':RES,'status':'candidate','notes':'33 ohm at host SCLK/MOSI/VSYNC sources, not on petal; tune by scope'},
        {'item':'Harness wire','quantity':10,'manufacturer_part_number':'TBD','source_url':GH,'status':'blocked','notes':'AWG26 candidate, insulation OD 0.76-1.0 mm within GH range; exact flexible wire/length/current derating not frozen'},
        {'item':'Host','quantity':1,'manufacturer_part_number':'NUCLEO-G474RE','source_url':'https://www.st.com/en/evaluation-tools/nucleo-g474re.html','status':'external-candidate','notes':'3.3V SPI+ADC host; pin allocation and firmware still need separate verification'},
        {'item':'Protected regulated 3.3V LED supply','quantity':1,'manufacturer_part_number':'TBD','source_url':DS,'status':'blocked','notes':'external supply, not Nucleo GPIO; >=0.350 A transient capability is 25% planning margin above 0.280 A; set current limit after inrush/cable review'},
        {'item':'Regulated 3.3V logic supply/VIO control','quantity':1,'manufacturer_part_number':'TBD','source_url':DS,'status':'blocked','notes':'VIO input-current/host-drive budget must be checked; common reference GND; power-order coordination required'}])
    save('netlist.json',{'format':'tool-neutral pin-level netlist; not an ECAD export','revision':'ULP-02',
         'components':components,'pins':pins,'nets':dict(nets),'no_connect_pins':[p for p in pins if p['net'] is None]})
    csvwrite('led-placement-reference.csv',[dict(p,side='F',rotation_deg=0,cathode_pin=1,anode_pin=2,
        dot_index=18*p['sw']+p['cs'],dc_address=f'0x{0x100+18*p["sw"]+p["cs"]:03X}',
        pwm_low_address=f'0x{0x200+2*(18*p["sw"]+p["cs"]):03X}') for p in pixels])
    installed={18*p['sw']+p['cs'] for p in pixels}
    masks=[0]*33
    for p in pixels:masks[3*p['sw']+p['cs']//8]|=1<<(p['cs']%8)
    dc=[255 if i in installed else 0 for i in range(198)]
    assert sum(bin(v).count('1') for v in masks)==113
    assert {18*row+col for row in range(11) for col in range(18)
        if masks[3*row+col//8] & (1<<(col%8))} == installed
    assert {i for i,v in enumerate(dc) if v} == installed
    assert all(spi_header(a,True)[0]*4+(spi_header(a,True)[1]>>6)==a for a in range(1024))
    config=[(0x000,[0],'outputs disabled'),(0x001,[0x5C],'11 lines; Mode3 16-bit; 125kHz'),
        (0x002,[0],'1us blanking; linear; no phase shift'),(0x003,[0],'baseline compensation/removal off'),
        (0x004,[0x51],'3mA first-light ceiling; weak down-deghost; up clamp VLED-2.5; enabled'),
        (0x005,[0,255,255,255],'master zero, three group PWM full'),(0x009,[127]*3,'all CC groups full'),
        (0x00C,[0]*55,'no per-dot group multiplication'),(0x043,masks,'only 113 populated sites ON'),
        (0x100,dc,'installed sites DC255; absent sites DC0'),(0x200,[0]*396,'all 16-bit pixel PWM zero'),
        (0x000,[1],'enable only after readback; remain dark, wait >=100us')]
    operations=[{'register':f'0x{a:03X}','length':len(b),'bytes':b,'spi_write_header':spi_header(a),
                 'spi_read_header':spi_header(a,False),'reason':note} for a,b,note in config]
    save('register-plan.json',{'revision':'ULP-02','not_executed_on_hardware':True,'SPI':{'mode':0,'msb_first':True,'initial_hz':100000,'target_hz_after_signal_test':2000000,
        'header_formula':'[(addr>>2), ((addr&3)<<6) | (write ? 0x20 : 0)]'},
        'power_up':['hold VIO_EN low; all host SPI/VSYNC outputs low or high-Z; external pullups disabled',
                    'apply regulated VCC/VLED, then raise VIO_EN to same 3.3V IO reference; wait >=500us',
                    'raise SS; execute operations and read back writable registers; do not write reserved address holes',
                    'after Chip_EN=1 wait >=100us; VSYNC high >=200us while not writing PWM; master/PWM remain zero'],
        'operations':operations,'twenty_mA_change':['Chip_EN=0','Dev_config3=0x59','read back config','Chip_EN=1','wait >=100us; submit separately reviewed frame and VSYNC'],
        'mode3_PWM_byte_order':'low byte then high byte; address=0x200+2*(18*sw+cs)',
        'reset_default_conflict':'SNVSBU8A table lists 0x47; SNVU786 section 2.2.5 lists 0x57. Do not rely on reset value; explicitly write and read back 0x51/0x59.',
        'sources':[DS,TRM]})
    count=Counter(p['sw'] for p in pixels)
    polygon=panel['cad_window_polygon_mm']
    area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]+polygon[:1])))/2
    budget={'board_outline_reference_mm':panel['cad_window_polygon_mm'],'outline_area_mm2':area,'board_outline_status':'same visible-window polygon as planning reference; no mounting/routing release',
      'board_stack_candidate':'4 layers, 0.8 mm finished FR4; stackup/impedance/fab tolerance not ordered',
      'LED_land_envelope_area_mm2':113*2.4*.8,'populated_by_row':dict(count),
      'I_peak_mA_20mA':max(count.values())*20,'I_avg_upper_mA_20mA':113*20/11,
      'I_avg_with_1us_blanking_mA_20mA':113*20/11*8/9,'P_VLED_upper_W':113*.020/11*3.3,
      'P_LED_typ_electrical_W':113*.020/11*2.,'P_U1_stage_typ_W':113*.020/11*(3.3-2.),
      'logic_allocation_W_not_max_spec':.050,'total_board_planning_W':.728,
      'uniform_area_heat_flux_W_cm2':.728/(area/100),'bulk_cap_nominal_uF':44,
      'worst_8us_pulse_droop_mV_C_only_nominal44uF':.280*8e-6/(44e-6)*1000,
      'droop_mV_Ceff20uF_assumption':.280*8e-6/(20e-6)*1000,
      'NTC_bias_R_ohm':47000,'NTC_25C_bias_uA':3.3/57000*1e6,
      'NTC_25C_voltage_V':3.3*10000/57000,
      'NTC_25C_self_heating_power_mW':(3.3/57000)**2*10000*1000,
      'NTC_all_R_nominal_max_power_mW':3.3**2/(4*47000)*1000,
      'NTC_ADC_RC_tau_25C_ms':(47000*10000/57000+1000)*1e-7*1000,
      'front_LED_height_max_mm':.8,'back_IC_max_mm':1.,'back_bulk_cap_max_mm':1.45,
      'GH_header_body_depth_mm':4.25,'GH_header_body_height_mm':4.05,'GH_header_standoff_reference_mm':.15,'GH_mated_reference_height_mm':7.3,
      'bare_board_LED_and_bulk_cap_stack_mm':3.05,'mated_root_stack_excluding_wire_bend_mm':8.9,
      'front_diffuser_gap_and_sheet_assumption_mm':1.4,'root_stack_with_front_assumption_mm':10.3,
      'excludes':['solder stand-off','PCB thickness tolerance','insulation to metal','wire bend/extraction clearance','mounting hardware','actual PCB routing and thermal field'],
      'NTC_height_max_mm':.95,
      'NTC_body_and_land_status':'Murata JEWB01BR-5300G p5 gives body and reflow ranges; library overlay still required'}
    save('mechanical-power-budget.json',budget)
    # Footprint dimensions are explicit candidates, not untested library files.
    qfp=[]
    for i in range(10):
        qfp.extend([{'pad':i+1,'xy_mm':[-2.4,1.8-.4*i],'size_mm':[.6,.2]},
                    {'pad':11+i,'xy_mm':[-1.8+.4*i,-2.4],'size_mm':[.2,.6]},
                    {'pad':21+i,'xy_mm':[2.4,-1.8+.4*i],'size_mm':[.6,.2]},
                    {'pad':31+i,'xy_mm':[1.8-.4*i,2.4],'size_mm':[.2,.6]}])
    qfp.append({'pad':41,'xy_mm':[0,0],'size_mm':[3.5,3.5]})
    save('footprint-constraints.json',{'coordinate_convention':'component mounting-side view, X right Y up; bottom-side placement must mirror the footprint in ECAD, never renumber pins',
       'TI_RKP0040B':{'body_mm':[5,5,1],'pads':sorted(qfp,key=lambda p:p['pad']),'source':DS+' (package pages 58-60)',
                      'thermal':'AGND/EP common copper; thermal vias and segmented paste per manufacturer example, assembler must qualify via filling and stencil'},
       'WE_150060YS75000':{'body_nominal_mm':[1.6,.8,.7],'pads':[{'pad':1,'name':'K','xy_mm':[-.8,0],'size_mm':[.8,.8]},{'pad':2,'name':'A','xy_mm':[.8,0],'size_mm':[.8,.8]}],'source':LED},
       'C0603':{'candidate_pads':[{'pad':1,'xy_mm':[-.7,0],'size_mm':[.8,.8]},{'pad':2,'xy_mm':[.7,0],'size_mm':[.8,.8]}],'source':TDK+'C1608X7R1E105K080AB','status':'chosen within TDK reflow land ranges; assembler review required'},
       'R0603':{'candidate_pads':[{'pad':1,'xy_mm':[-.8,0],'size_mm':[.9,.95]},{'pad':2,'xy_mm':[.8,0],'size_mm':[.9,.95]}],'source':RES,'status':'engineering land candidate; match current manufacturer reflow recommendation before library release'},
       'C0805':{'candidate_pads':[{'pad':1,'xy_mm':[-.95,0],'size_mm':[1,1.4]},{'pad':2,'xy_mm':[.95,0],'size_mm':[1,1.4]}],'source':TDK+'C2012X5R1V226M125AC','status':'engineering land candidate; not released'},
       'NTC0603':{'electrical_pins':[1,2],'body_nominal_mm':[1.6,.8,.8],'body_tolerance_mm':.15,
           'manufacturer_reflow_land_ranges_mm':{'a':[.6,1.0],'b':[.6,.7],'c':[.6,.8]},
           'source':NTC+' (p5, JEWB01BR-5300G)','status':'controlled body/ranges available; mapping a,b,c to actual land requires graphic/library overlay before release'},
       'JST_GH_10_TOP':{'pitch_mm':1.25,'first_to_last_pin_mm':11.25,'header_width_B_mm':15.75,'signal_pad_mm':[.6,1.7],
                        'hold_down_pad_mm':[1,2.8],
                        'pads':[{'pad':i+1,'xy_mm':[5.625-1.25*i,1.95],'size_mm':[.6,1.7]} for i in range(10)]+[
                          {'pad':'M1','xy_mm':[7.475,-1.4],'size_mm':[1,2.8]},
                          {'pad':'M2','xy_mm':[-7.475,-1.4],'size_mm':[1,2.8]}],
                        'source':GH+' (pages 2-3)',
                        'status':'public catalogue geometry visually checked using PDFium: pin1 upper right in manufacturer mounting-side view; signal length 5.6-3.9=1.7; complete model drawing/production library review still required'},
       'routing':{'layers_candidate':4,'finished_thickness_mm':.8,'external_copper_oz_candidate':1,'min_trace_clearance_mm_candidate':[.15,.15],
          'SW_distribution_width_mm_candidate':.5,'SW_escape_width_mm_candidate':.15,'VLED_GND_trunk_goal_mm':.8,'CS_distribution_width_mm_candidate':.2,'CS_escape_width_mm_candidate':.15,
          'exceptions':'QFN escapes may be 0.15 mm; several scan interconnects also use 0.15/0.20 mm. Actual width/length/resistance audit governs; no thermal-current approval inferred',
          'planes':'continuous GND reference; VLED distribution separated from NTC trace; no isolated AGND island',
          'critical':'local decouplers same side as U1, shortest direct pad loops and nearby return vias; current SW traces wider than CS; keep all non-LED parts behind board',
          'contact_reserve':panel['contact_reserve_mm'],'no_LED_coordinate_changes':True,
          'unresolved':'PCB support and passage under full contact band including tip pixel at x128 need mechanical review; no holes, supports or copper currently generated'}})
    draw_schematic(components,pins);draw_matrix(pixels)
    # Layout reference is deliberately independent of copper/routing.
    s=svg_start(1300,580,'UPPER PETAL / HLIO-R03 ELECTRICAL COUPON','Front coordinates unchanged. Rear rectangles are reservations, NOT copper / footprints / final arm assembly data.')
    def xy(x,y):return (35+(x-15)*10,280-y*10)
    pts=' '.join(f'{xy(x,y)[0]},{xy(x,y)[1]}' for x,y in panel['cad_window_polygon_mm'])
    s.append(f'<polygon points="{pts}" fill="#eef4f7" stroke="#173744"/>')
    reserve=panel['contact_reserve_mm'];lo=reserve['along_center']-12;hi=reserve['along_center']+12
    x,y=xy(lo,23);s.append(f'<rect x="{x}" y="{y}" width="{(hi-lo)*10}" height="460" fill="#b06666" opacity=".16"/>')
    for p in pixels:
        x,y=xy(p['x_mm'],p['y_mm']);s.append(f'<rect x="{x-12}" y="{y-4}" width="24" height="8" fill="#f3b54a" stroke="#aa741e"/>')
    for ref,x,y,w,h in [('J1',24,0,8,19),('U1',43,0,6,6),('rear passives',55,0,26,13),('NTC',76,0,4,4)]:
        xx,yy=xy(x-w/2,y+h/2);s.append(f'<rect x="{xx}" y="{yy}" width="{w*10}" height="{h*10}" fill="none" stroke="#1b7b89" stroke-dasharray="5 3"/>');text(s,xx,yy-6,ref,12)
    text(s,35,514,f'Reference polygon area {area:.2f} mm2. No mounting holes. 113 XY fixed; use ULP-02 electrical mapping only.',15)
    text(s,35,541,'Contact band is a physical integration hold: do not place PCB over the gripping pad or treat the light as a load path.',15)
    s.append('</svg>');(OUT/'placement-reference.svg').write_text('\n'.join(s))
    sources=[{'id':'U1-DS','url':DS,'checked':'61-page Rev A; pin table, SPI, timing, current and package drawings'},
        {'id':'U1-TRM','url':TRM,'checked':'config pp30-36, onoff pp70+, DC p140, 16-bit PWM p205; reset-default conflict recorded'},
        {'id':'EVM','url':EVM,'checked':'schematic p14 and BOM p15; reference, not copied complete EVM'},
        {'id':'LED','url':LED,'checked':'p1 polarity/land/max ratings and p2 Vf; official PDF fetched and visually inspected'},
        {'id':'GH','url':GH,'checked':'p2-3 rendered with PDFium after Poppler missing glyphs: 1.7 signal-pad length; pin1 upper right; 4.25 is depth, 4.05 body height +0.15 standoff; mated reference 7.3; controlled model drawing not obtained'},
        {'id':'R','url':RES,'checked':'CRCW0603 ordering code and rated family; quantity values are project choices'},
        {'id':'NTC','url':NTC,'checked':'official 22-page JEWB01BR-5300G; p3 F-series table, p5 dimensions/land ranges; 0.1mA means 0.1C self-heating in specified 25C still-air test, not universal absolute-current rating'},
        {'id':'NCP-NRND','url':'https://www.murata.com/products/thermistor/ntc/overview/lineup/ncp','checked':'NCP15/18 NRND, updated 2025-03-31; NCU recommended for new designs'},
        {'id':'GH-CAD-access','url':'https://www.jst-mfg.com/product/index.php?doc=4&filename=BM10B-GHS-TBT.pdf&series=105&type=10','checked':'2025 onward drawings distributed by email after company/contact form; no form submitted, no external contact'},
        *[{'id':p,'url':TDK+p,'checked':'official indexed part data; bulk capacitor also in TI EVM BOM'} for p in ['C2012X5R1V226M125AC','C1608X7R1E105K080AB','C1608X7R1H104K080AA','C1608C0G1H102J080AA']]]
    save('sources.json',{'accessed':'2026-09-27','sources':sources,'input_pixel_source_sha256':digest(PIXEL_SOURCE)})
    output_files=[p for p in OUT.iterdir() if p.suffix in ['.json','.csv','.svg'] and p.name!='verification.json']
    save('verification.json',{'revision':'ULP-02','status':'this generator validates pin-level consistency and data mapping only; actual ECAD results are maintained separately in kicad/checks/verification.json',
       'kicad_availability':'historical initial lookup: absent from PATH and standard application locations. Subsequent local KiCad 10.0.6 install verified; current actual CLI/ERC/DRC results are in kicad/checks/verification.json; runtime hashes in kicad/toolchain-plan.json',
       'component_count':len(components),'LED_count':len(pixels),'connected_net_count':len(nets),'pin_records':len(pins),'U1_float_pins':[p['pin'] for p in pins if p['ref']=='U1' and p['net'] is None],
       'checks':['all component pins unique and enumerated','all connected nets have at least two nodes','113 unchanged XY positions, unique physical-adjacency SW/CS mapping','each LED pin2=A=SW and pin1=K=CS','all40U1 pins+EP41 covered','4unusedCS pins explicitly NC','unused LED sites OFF/DC0/PWM0','16bit row-major SRAM address mapping','SPI address headers stay10bit'],
       'input_hashes':{'docs/engineering/sources/head-lighting-io.json':digest(PIXEL_SOURCE),'engineering/electronics/upper-petal-prototype/ulp02/build.py':digest(Path(__file__))},
       'output_hashes':{p.name:digest(p) for p in sorted(output_files)},'not_done':['for native ECAD state see kicad/checks/verification.json','Gerber','stencil','assembler polarity check','electrical bring-up','thermal tests','mechanical integration']})
    print(json.dumps({'components':len(components),'pins':len(pins),'nets':len(nets),'leds':113,'nominal_area_mm2':area,'status':'review package generated, not fabrication release'}))


if __name__=='__main__':main()
