# SPDX-License-Identifier: CC-BY-NC-4.0
"""Controlled RFQ/first-article definition; never a physical production release.

Electronics children come from native exports, not a second hand-maintained BOM.
Open harness parts have explicit unknown lengths and cannot become purchase-ready.
"""
import csv,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE/'build';ELEC=HERE.parent/'electronics'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
io=ELEC/'base-io-b05/manufacturing/b06-io-prototype/B06-IO-Native-BOM.csv'
lamp=ELEC/'base-light-b06/manufacturing/bom.csv'
rows=[]
for r in csv.DictReader((OUT/'B06-mechanical-bom.csv').open(encoding='utf-8-sig')):
    rows.append(dict(id=r['id'],parent='BASE',quantity=r['quantity'],unit='pcs',
        kind='assembly_parent' if r['category']=='electronics' else r['category'],
        specification=r['specification'],manufacturer_part='',source=r['cad_files'],
        status='RFQ_CANDIDATE',open_item=r['notes']))
for parent,path,n in [('PCB-B06-IO',io,6),('PCB-B06-LIGHT',lamp,12)]:
    native=list(csv.DictReader(path.open(encoding='utf-8-sig'),delimiter='\t'))
    assert sum(int(r['Quantity']) for r in native)==n
    for r in native:
        assert r['Manufacturer Part'] and r['Designator']
        rows.append(dict(id=parent+'/'+r['Designator'],parent=parent,quantity=r['Quantity'],unit='pcs',kind='component_child',
            specification=r['Value'] or r['Comment'],manufacturer_part=r['Manufacturer Part'],
            source=str(path.relative_to(HERE.parent)),status='NATIVE_BOM_VERIFIED',
            open_item='Supplier availability/lot and PCBA process must be confirmed; buy either populated parent or children'))
extras=[
 ('W01',1,'operation','weld_process','Four continuous 140mm fillets; z5, proposed leg5.0..5.5; postweld datum machining','','WPS, bead profile, end allowance, distortion and joint strength unqualified'),
 ('EXT-48V-MATE',1,'pcs','connector','Phoenix PC5/2 mating spring plug','1718481','Real ClickLock operation / conductor preparation / cable exit fit'),
 ('RF-BULKHEAD',2,'pcs','connector','Amphenol SMA female-female 50ohm bulkhead','132170','Current manufacturer drawing and actual nut/tool fit required; GMSL channel/PoC not qualified'),
 ('POWER-M3-LUG',2,'pcs','terminal_candidate','TE M3 ring lug; 1.5..2.5mm2; plate0.79mm','165295','Actual tolerance, crimp tool, wire gauge/current/length, barrel rotation and boot required'),
 ('BOND-M3-LUG',1,'pcs','terminal_candidate','TE M3 ring lug at J6; never use power return as chassis bond','165295','Bond conductor and topology to external box require definition'),
 ('STUD-HALF-NUT',3,'pcs','hardware_candidate','M3 ISO4035 thin nut; nominal1.8mm; no extra washer','','Not released: tolerance/full-thread engagement/retention/anti-rotation and torque sample tests'),
 ('FRAME-BOND-LUG',1,'pcs','terminal_candidate','TE M6 ring lug at dedicated frame hole','165299','Drawing, cross section, crimp and grounding contact preparation required'),
 ('FRAME-BOND-SCREW',1,'pcs','hardware_candidate','M6 screw + contact locking hardware','','Length/stack/thread engagement and MCAD/tool clearance must be selected before purchase'),
 ('H-POWER',1,'assembly','harness_open','48V + return from J4/J5 to module boundary','','Gauge/current/length/ends/boots/clamps unknown; no arm harness required for base dummy load'),
 ('H-BOND',1,'assembly','harness_open','J6 to metal frame and external protective-bond boundary','','Topology/length/cross section and low resistance acceptance not frozen'),
 ('H-ECAT',1,'assembly','harness_open','Internal shielded Ethernet J2 to module boundary; two-ended base loopback test','','Exact cable/plug/length; shield termination and fixed bend radius to be checked'),
 ('H-RF',2,'assembly','harness_open','50ohm coax from bulkhead to module-side test connector','','Connector family/length/route/minimum bend/channel budget/PoC unknown'),
 ('H-LAMP',1,'assembly','harness_open','Internal short lead only: base board to JST GH 1=5V 2=PWM 3=GND','GHR-03V-S + 3xSSHL-002T-P0.2','No separate desk-box5V lead; local converter and PWM circuit pending; actual length/colors/crimp/route unknown'),
 ('LOCAL-5V-CONVERTER',1,'pcs','power_candidate','PCB mounted non-isolated DC/DC 9..72V input,5V/500mA;11.5x8.5x17.5mm','R-78HB5.0-0.5','Candidate only; not present on current native IO PCB; footprint, protection, output tolerance and thermal/EMI check pending'),
 ('LOCAL-5V-CIN',1,'pcs','power_open','3.3uF/100V input capacitor per converter >50V application','','Exact capacitor/derating/ripple and placement pending'),
 ('LOCAL-5V-BLEED',1,'pcs','power_open','470ohm1%,>=0.125W:10.0..11.3mA at4.75..5.25V minimum-load candidate','','Required if no other always-on10mA load; not fitted on current native PCB'),
 ('LIGHT-SHIM',2,'pcs','optical_open','Soft optical-support pad; current nominal support gap at least0.4mm','','Material/thickness/compression/translucency measured on actual printed lens'),
 ('CABLE-RESTRAINT',1,'set','consumable_open','Rounded ties / saddles at existing carrier ears; wire boots and insulated separation','','Count/position/tool and pull-force criteria after actual harness route'),
 ('FINISH',1,'operation','finish_open','Deburr, corrosion protection; mask bond faces/threads/datum seats','','Coating and weld preparation agreed with supplier; no coating in conductive bond interface'),
]
for id,q,u,k,s,mpn,issue in extras:
    rows.append(dict(id=id,parent='BASE',quantity=q,unit=u,kind=k,specification=s,manufacturer_part=mpn,
        source='manufacturing.md',status='DEFINITION_OPEN',open_item=issue))
assert len({r['id'] for r in rows})==len(rows)
with (OUT/'B06-manufacturing-bom.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
checks=[
 ('FAI-01','incoming','All parts','Material/lot/MPN; 5 product prints; PCB child BOM quantities6/12','Record certificates/lot labels and visual condition'),
 ('FAI-02','weld_before_finish','W01','Four seams z5; leg5.0..5.5 provisional envelope; 140mm each','WPS signoff and actual weld profile/end termination inspection'),
 ('FAI-03','postweld','B06-101','Deck upper datum Z17; flatness<=0.15 candidate','Surface plate/indicator; measure after welding, machining and finish'),
 ('FAI-04','postweld','W01','M12 axes / upper-lower plane relationship to CAD','CMM + thread gauges; record full measured coordinates; tolerance allocation not released'),
 ('FAI-05','install','W01/desk','Actual desk edge remains clear of front weld incl. measured bead and pad','Measure real minimum gap; no contact allowed; nominal0.5mm is NOT tolerance qualification'),
 ('FAI-06','machining','B06-104','OD160 ID56 Z58; PCD120 8M6 phase22.5; 4 post seats','CMM to common datum frame; identify concentricity/pattern errors; refer interface contract'),
 ('FAI-07','machining','B06-105 x4','D18 length29; M8 blind thread depth/bolt tips3mm nominal clearance','GO/NO-GO and depth gauge; do not mistake drill depth for full thread'),
 ('FAI-08','machining','All metal','Bore/thread/counterbore/profile match individual STEP + drawing table','No unapproved missing holes; no sharp edges in wire paths'),
 ('FAI-09','printing','5 printed parts','Actual STL matches source hash; nut-pocket and optical-gap measurements','Printer/material/lot/profile and measured shrinkage; dry assembly without forcing'),
 ('FAI-10','PCBA','IO + lamp','Native DRC, Gerber/IPC356 and exact MPN BOM; reflow THR studs','Assembler signs mixed process; solder inspection and continuity/polarity test'),
 ('FAI-11','terminal_stack','J4 J5 J6','3+-0.2mm stud vs lug + thin nut total maximum','Record actual stack/full engaged threads/locking method; current candidate NOT released'),
 ('FAI-12','bonding','Frame/J6','Dedicated bond contact, finish mask and return separation','Record crimp, length, screw seating and measured resistance; contract threshold to be frozen'),
 ('FAI-13','harness','All harnesses','Each physical route: length/bend/clamp/boot and mating/release','Measured length drawing; both-end pin test; no wire pinched by cover or fastener'),
 ('FAI-14','assembly','Cover and IO','Tool paths + real nuts/plug latches + rear cover removal','Repeat assembly; record no forced fit/PCB bow/blocked release'),
 ('FAI-15','optical','Lamp','5V independent bench supply <=100mA initial; PWM1kHz','Check off/dim/breath/flash and LED-to-lens gap; never connect48V to lamp'),
 ('FAI-16','shelf','Tray','180x150x50 budget,3kg target; inward extraction','Restrained standalone test; actual clamp retention and vent/cable clearance'),
 ('FAI-17','test_fixture','T01/T02','Fixture dimensional/fastener/rated apparatus qualification','No150Nm loading before fixture and equipment review'),
 ('FAI-18','qualification','Base only','20 independent tests per validation-plan.json','Real operator/reviewer/calibrated instrument/files; qualification.py binds this version'),
 ('FAI-19','release','All documents','Current BOM/STEP/STL/PDF/native-PCB/harness/process hashes agree','Accountable review signature and repeat-build records; no automatic production approval'),
]
traveler=[dict(id=id,stage=st,part=p,design_requirement=req,inspection=ins,measured_value='',instrument='',operator='',date='',result='NOT_MEASURED',evidence='') for id,st,p,req,ins in checks]
with (OUT/'B06-first-article-traveler.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(traveler[0]));w.writeheader();w.writerows(traveler)
definition={'revision':'B06-COMPACT-07-DFM','production_released':False,'arm_required':False,
 'bom_lines':len(rows),'native_IO_component_quantity':6,'native_lamp_component_quantity':12,
 'first_article_steps':len(traveler),'procurement_rule':'Populated PCBA parent OR its bare board/component children; never both',
 'open_definition_items':[r['id'] for r in rows if r['status']=='DEFINITION_OPEN'],
 'stud_stack_screen':{'thread_height_min_mm':2.8,'lug_nominal_mm':.79,'ordinary_nut_nominal_mm':2.4,
    'ordinary_stack_nominal_mm':3.19,'ordinary_stack_full_engagement_feasible':False,
    'thin_nut_candidate_mm':1.8,'candidate_nominal_stack_mm':2.59,
    'candidate_gap_to_min_thread_mm':.21,'tolerances_and_retention_qualified':False},
 'sources_sha256':{str(p.relative_to(HERE.parent)):sha(p) for p in [io,lamp,HERE/'manufacturing.md',OUT/'B06-mechanical-bom.csv']},
 'digital_definition_check':'Native BOM child counts, unique IDs and source hashes only; open items are NOT qualified'}
(OUT/'manufacturing-definition.json').write_text(json.dumps(definition,ensure_ascii=False,indent=2)+'\n')
print('MANUFACTURING_DEFINITION',len(rows),'BOM lines;',len(traveler),'unmeasured first-article steps; production=False')
