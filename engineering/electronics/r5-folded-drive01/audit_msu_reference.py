#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Audit separately obtained original KSS IGES. Does not redistribute its BREP."""
from pathlib import Path
import argparse,json,hashlib
import cadquery as cq
from OCP.IGESControl import IGESControl_Reader
p=argparse.ArgumentParser();p.add_argument('vendor_iges',type=Path);a=p.parse_args()
r=IGESControl_Reader();assert int(r.ReadFile(str(a.vendor_iges)))==1;r.TransferRoots();s=cq.Shape.cast(r.OneShape());fs=s.Faces()
assert len(fs)==130 and len(s.Solids())==0
# Groups were matched to the official assembly section, not inferred as solid bodies.
groups={'body':(0,48),'pressure_cover':(48,54),'bearing_reference_1':(54,68),'locknut_including_screw':(68,110),'collar':(110,116),'bearing_reference_2':(116,130)}
def bb(sh):
 b=sh.BoundingBox();return [round(v,5) for v in (b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax)]
G={k:{'face_index_range_half_open':list(v),'bbox_mm':bb(cq.Compound.makeCompound(fs[v[0]:v[1]]))} for k,v in groups.items()}
assert G['body']['bbox_mm'][4:]==[-17.,0.]
assert G['bearing_reference_1']['bbox_mm'][4:]==[-14.5,-8.75]
assert G['bearing_reference_2']['bbox_mm'][4:]==[-8.75,-3.]
assert G['locknut_including_screw']['bbox_mm'][4:]==[2.5,7.5]
assert G['collar']['bbox_mm'][4:]==[-3.,2.5]
o=dict(revision='R5-FOLDED-DRIVE01',source_url='https://www.kss-superdrive.co.jp/jp/cad/3d/MSU6C.zip',vendor_member='MSU6C/MSU6C.igs',iges_sha256=hashlib.sha256(a.vendor_iges.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),faces=len(fs),solids=len(s.Solids()),overall_bbox_mm=bb(s),reference_groups=G,
 nominal_inference=dict(native_shoulder_z_mm=-14.5,native_nut_front_z_mm=7.5,difference_mm=22.,catalogue_cross_check='MSU-6C E107-108 reference (L2)=22mm, not a tolerance-controlled chain',screw_fixed_end_length_mm=30.,inferred_tip_to_nut_mm=8.,coupling_insert_mm=6.5,nominal_gap_mm=1.5),
 unresolved=['IGES reference-bearing spans total11.5mm; separate MTA06-15HP5DF catalogue lists single B5.5. Do not use IGES as bearing preload/width authority.','Inference assumes proper shoulder seating. Actual tolerance stack, collar/nut adjustment, chamfer and wrench access remain unverified.','IGES surfaces are not closed solids; no claimed interference-volume or installed mass validation.'],manufacturer_geometry_redistributed=False)
(Path(__file__).parent/'msu-reference-audit.json').write_text(json.dumps(o,indent=2)+'\n');print('MSU nominal-reference audit PASS; dimensional limitations retained')
