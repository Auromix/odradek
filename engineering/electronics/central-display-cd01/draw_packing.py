#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json,csv,html
D=Path(__file__).resolve().parent;m=json.loads((D/'mechanical-packing.json').read_text());dots=list(csv.DictReader((D/'pixel-map.csv').open()))
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="810" viewBox="0 0 1440 810">','<rect width="1440" height="810" fill="#f4f2eb"/>','<style>text{font-family:Arial,sans-serif;fill:#162d3a}.small{font-size:13px}.body{font-size:16px}.title{font-size:27px;font-weight:bold}</style>']
def tx(t,x,y,cls='body',anchor='start'):s.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{html.escape(t)}</text>')
scale=8
cx=[365,1080];cy=370
for c in cx:
 s+= [f'<circle cx="{c}" cy="{cy}" r="240" fill="#fcfcf8" stroke="#283f49" stroke-width="2"/>',f'<circle cx="{c}" cy="{cy}" r="224" fill="none" stroke="#929f9a" stroke-dasharray="5 5"/>',f'<path d="M{c-255},{cy}H{c+255} M{c},{cy-255}V{cy+255}" stroke="#dce2dc"/>']
tx('CD-EC01 / Central display / packing witness',35,43,'title');tx('Schematic candidate — no native PCB, routing or fabrication release',35,72)
tx('FRONT: 285 unchanged LED coordinates',cx[0],105,'body','middle');tx('BACK COMPONENTS: head XY projection',cx[1],105,'body','middle')
for p in dots:
 x=cx[0]+scale*float(p['x_mm']);y=cy-scale*float(p['y_mm']);color='#b57316' if p['driver']=='A' else '#255f73'
 s.append(f'<rect x="{x-9.6}" y="{y-3.6}" width="19.2" height="7.2" fill="{color}"/>')
for a in m['components']:
 lo,hi=a['envelope_head_min_mm'],a['envelope_head_max_mm'];x=cx[1]+scale*lo[0];y=cy-scale*hi[1];w=scale*(hi[0]-lo[0]);h=scale*(hi[1]-lo[1]);col='#e4d0a3' if a['ref']=='J1' else '#b8d2d6' if a['ref'].startswith('U') else '#dce7df'
 s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}" stroke="#466369" stroke-width=".8"/>');tx(a['ref'],x+w/2,y+h/2+4,'small','middle')
for t in m['thermal_bridge_candidate_regions']:
 x,y=t['center_xy_mm'];s.append(f'<rect x="{cx[1]+8*(x-2)}" y="{cy-8*(y+2)}" width="32" height="32" fill="none" stroke="#bf6847" stroke-dasharray="3 2"/>')
pin=m['connector']['CD01_parent_layout_input']['pin1_land_center_head_mm'];s.append(f'<circle cx="{cx[1]+8*pin[0]}" cy="{cy-8*pin[1]}" r="3" fill="#a33120"/>');tx('pin 1',cx[1]+85,cy+90,'small')
s.append(f'<path d="M{cx[1]},{cy+170}v45 l-7,-10 m7,10 l7,-10" fill="none" stroke="#95622a" stroke-width="2"/>');tx('wire exit -Y',cx[1]+12,cy+214,'small')
tx('A:142 sites / B:143 sites / each 11 scan rows x up to13 sinks',55,649);tx('13 x 20mA each driver: 0.52A combined peak; 3mA initial setting',55,674);tx('Front 2.4x0.9mm land/body envelope; max R27.4438 < aperture R28.5',55,699,'small')
tx('33 rear components; nominal mated GH + pad envelope included',760,649);tx('Max R21.6172 < reserved R28; lowest Z-7.45 > reserved Z-10',760,674);tx('Dashed boxes: optional 4x4mm no-component thermal patches',760,699,'small')
tx('All dimensions in mm. Back is projected through PCB in HEAD coordinates, not a back-side assembly view.',35,741,'small');tx('GH catalogue references only; wire bends, latch/tool travel, tolerances, thermal bridge and fabrication stack remain unverified.',35,765,'small');tx('Original drawing: Auromix contributors / CC BY-NC 4.0',35,791,'small')
s.append('</svg>');(D/'packing-review.svg').write_text('\n'.join(s)+'\n')
