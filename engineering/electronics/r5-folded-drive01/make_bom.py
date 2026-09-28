#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import csv,json
P=Path(__file__).resolve().parent;R=P.parents[2]
S=json.loads((R/'docs/engineering/sources/r5-folded-drive01.json').read_text());U={s['id']:s['url'] for s in S['sources']}
rows=[]
def row(id,qty,mpn,desc,mass,basis,status,source,gap):rows.append(dict(id=id,qty=qty,manufacturer_part_or_request=mpn,description=desc,unit_mass_kg=mass,mass_basis=basis,selection_status=status,source_url=U.get(source,source),remaining_gap=gap,budget_price='TBD'))
row('FD-B01',1,'Gates180-3MGT3-6 /9400-53250','3mmGT3;60teeth;180mm pitch;6mm width; same belt catalogue alternative code SDP A36R53M060060',.003,'2024 catalogue','candidate','FD04','Exact delivered regional belt identity/current availability; reversing registration/tension/life')
row('FD-P01',2,'SDP/SI A 6D53M030DF0906','30T3mm;6mm bore;FairlocM3;L20.6±.4;flange31.8±.4','','TBD; geometric proxy separate','candidate','FD01','Exact6mmM3 slip/installation torque; flange plane; runout; mass/inertia')
row('FD-C01',1,'NBK MST-16C-5-6','Motor5 to jackshaft6;L23;insertion6.5 each;rotating reference17.6',.0092,'largest-bore catalogue reference only','candidate','FD05','Actual selected variant mass/J/slip and combined misalignment/tool access')
row('FD-C02',1,'NBK MST-16C-4.5-6','Screw4.5 to jackshaft6;L23;insertion6.5 each;rotating reference17.6',.0092,'largest-bore catalogue reference only','candidate','FD05','KSS nominal1.5mm axial gap lacks tolerance and wrench clearance')
row('FD-BR01',4,'SKF626-2Z','6x19x6;C2340N;C0950N;limiting40krpm',.0088,'catalogue','candidate','FD09','Fits/retention/floating outer ring/alignment and friction/temperature')
row('FD-SH01',2,'CUSTOM-JACKSHAFT-01 (not a supplier SKU)','Ø6 seats;shoulderØ9;nominal51.5 overall; original requirement drawing','','TBD; nominal steel proxy separate','blocked','engineering/electronics/r5-folded-drive01/shaft-interface-requirements.svg','Journal fits/retainer grooves/material/heat treatment/finish/runout not frozen')
row('FD-H01',1,'TBD custom split bearing bridge','Two axes45mm; bearings atZ0..6 and32..38; whole motor/cartridge can translate for tension','','unallocated','TBD','engineering/electronics/r5-folded-drive01/layout-parameters.json','Actual housing/fasteners/retainers/tension actuator/assembly access not designed')
row('FD-G01',1,'TBD custom guard','Belt and coupling isolation; no self-locking or brake claim','','unallocated','TBD','','Envelope and retention/ventilation not designed')
row('FD-M01',1,'FAULHABER3274G024BP4 /PN3274.00001','Inherited24V motor; no gearbox',.325,'catalogue','candidate','FD10','0.140Nm zero-speed value remains graph-read thermal budget, not installed guarantee')
row('FD-E01',1,'IE3-1024L','Inherited encoder;3274 combination body90.8±.6',.0135,'typical catalogue','candidate','FD11','Encoder harness/total actual combined mass and screw clearances')
row('FD-SC01',1,'SG0802.5-080R130C5B1X (configuration request)','Inherited130mm total2.5mm lead request; stock mother SG0802.5-129R170C5','','TBD; geometric proxy separate','candidate','FD12','Not factory-accepted SKU; circulation acceleration/actual J/end machining/stroke/limits')
row('FD-SU01',1,'KSS MSU-6C','Inherited fixed support; includes factory bearing pair/collar/locknut',.050,'catalogue','candidate','FD13','Nominal CAD/table22mm cross-check; tolerance/tool access/installed axial duty')
row('FD-SU02',1,'KSS MSU-6CS','Inherited support side; do not duplicate axial locating',.032,'catalogue','candidate','https://kssballscrew.com/us/pdf/catalog/E109-E110.pdf','B-end request and final bearing alignment')
row('FD-GD01',2,'HIWIN MGN9C','Inherited guide blocks; combined rail request MGN9C2R115Z0HM',.016,'catalogue','candidate','https://www.hiwin.com/wp-content/uploads/Linear_Guideway-E.pdf','Original common90 rod force only; new carrier offsets/fasteners/limits not checked')
row('FD-GD02',1,'MGN rail115mm (configuration request)','Inherited9mm rail; mass.38kg/m',.0437,'catalogue per length','candidate','https://www.hiwin.com/wp-content/uploads/Linear_Guideway-E.pdf','Request identity/actual rail and support geometry')
with (P/'bom.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(f'{len(rows)} BOM rows; zero purchase/fabrication release')
