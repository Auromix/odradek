#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Original MCAD reference assembly from actual native PCB readback; not vendor component CAD."""
from pathlib import Path
import json,hashlib,math
import cadquery as cq
D=Path(__file__).resolve().parents[1];O=D/'mechanical';O.mkdir(exist_ok=True)
R=json.loads((D/'native-readback.json').read_text());M=json.loads((D/'mechanical-interface.json').read_text());A=cq.Assembly(name='B04_SERVICE01')
board=cq.Workplane('XY').box(80,50,1.6,centered=(False,False,False))
for h in R['holes']+[dict(uv_mm=v['uv_mm'],drill_mm=[v['drill_mm']]*2) for v in R['vias']]:
 x,y=h['uv_mm'];d=h['drill_mm'][0];assert abs(d-h['drill_mm'][1])<1e-6;board=board.cut(cq.Workplane('XY').center(x,y).circle(d/2).extrude(1.6))
assert board.val().isValid();A.add(board,name='PCB_drilled_native',color=cq.Color(.10,.32,.22))
rows=[]
def box(name,lo,hi,color,scope):
 dims=[hi[i]-lo[i] for i in range(3)];assert min(dims)>0
 s=cq.Workplane('XY').box(*dims,centered=(False,False,False)).translate(tuple(lo));assert s.val().isValid();A.add(s,name=name,color=cq.Color(*color));rows.append(dict(name=name,scope=scope,bbox_min_mm=lo,bbox_max_mm=hi,volume_mm3=s.val().Volume(),solid_valid=True))
for c in M['components']:
 color=(.14,.15,.17) if c['ref'][0] in 'ULDQ' else (.62,.49,.25) if c['ref'][0]=='C' else (.20,.48,.25) if c['ref'][0]=='J' else (.33,.34,.35)
 box(c['ref'],c['body_bbox_board_min_mm'],c['body_bbox_board_max_mm'],color,'placed maximum/reference package envelope including solder planning height, not detailed BREP')
for h in R['holes']:
 if h['type']!='PTH':continue
 # Cylinders bounded by actual finished hole; specified trimming must keep z>=-2.5.
 x,y=h['uv_mm'];rad=h['drill_mm'][0]*.35
 s=cq.Workplane('XY').center(x,y).circle(rad).extrude(2.5).translate((0,0,-2.5));A.add(s,name='pin_'+h['ref']+'_'+h['pin'],color=cq.Color(.68,.69,.7))
for c in M['connectors']:
 # Only the portion beyond header body is a new solid; full mated reference remains JSON.
 lo=[*c['mated_uv_box'][0],c['mated_z_mm'][0]];hi=[*c['mated_uv_box'][1],c['mated_z_mm'][1]]
 if c['ref'] in ['J1','J2']:hi[0]=c['header_uv_box'][0][0]
 else:lo[0]=c['header_uv_box'][1][0]
 box(c['ref']+'_mating_plug_extension',lo,hi,(.38,.57,.39),'catalogue reference/clearance envelope; not exact mating connector vendor CAD')
# Connector full mated height also extends over the header; keep independent review object.
for c in M['connectors']:
 ref=next(r for r in M['components'] if r['ref']==c['ref']);lo=[*c['header_uv_box'][0],ref['body_bbox_board_max_mm'][2]];hi=[*c['header_uv_box'][1],c['mated_z_mm'][1]]
 if hi[2]>lo[2]:box(c['ref']+'_mated_height_reservation',lo,hi,(.56,.68,.48),'mated reference height reservation, not mass-bearing body')
A.save(str(O/'base-b04-local.step'));A.save(str(O/'base-b04-local.glb'))
G=cq.Assembly(name='B04_ASSEMBLY_COORDINATES');G.add(A,loc=cq.Location(cq.Vector(*M['global_origin_mm'])),name='B04_SERVICE01');G.save(str(O/'base-b04-assembly.step'))
cq.exporters.export(board,str(O/'base-b04-board-only.step'))
sh=A.toCompound();bb=sh.BoundingBox();z=dict(revision=M['revision'],board_sha256=R['board_sha256'],model_scope=M['model_scope'],board_solid_valid=board.val().isValid(),assembly_solid_count=len(sh.Solids()),board_volume_mm3=board.val().Volume(),component_reference_objects=rows,bbox_local_min_mm=[bb.xmin,bb.ymin,bb.zmin],bbox_local_max_mm=[bb.xmax,bb.ymax,bb.zmax],global_origin_mm=M['global_origin_mm'],files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(O.iterdir()) if p.suffix in ['.step','.glb']},mass_kg=None,manufacturing_release=False)
(O/'verification.json').write_text(json.dumps(z,indent=2)+'\n');print('MCAD',z['assembly_solid_count'],'solids',z['bbox_local_min_mm'],z['bbox_local_max_mm'])
