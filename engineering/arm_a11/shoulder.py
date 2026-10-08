# SPDX-License-Identifier: CC-BY-NC-4.0
"""Removable shoulder bridge armour; two through-bolts, captive nuts, fixed datums.
Assembly is a supported fit prototype, not a structural/load release.
"""
import json,math,numpy as np,cadquery as cq
from shapely.geometry import LineString
import interfaces as c
b=c.legacy;OUT=c.OUT

def prism(poly,y,h):
 pl=cq.Plane(origin=b.V([0,y,0]),normal=b.V([0,-1,0]),xDir=b.V([1,0,0]))
 return cq.Workplane(pl).polyline(list(poly.exterior.coords)[:-1]).close().extrude(h).val()

def main():
 D=json.loads((OUT/'manifest.json').read_text());b.OUT=OUT;b.PARTS[:]=D['parts'];b.SHAPES.clear();c.HARDWARE[:]=[h for h in D['hardware'] if not h['id'].startswith('S01-')]
 for p in b.PARTS:
  if p['role']=='hardware' or p['id']=='P01-shoulder-monobloc':b.SHAPES[p['id']]=cq.importers.importStep(str(OUT/'step'/f"{p['id']}.step")).val()
 from shapely.geometry import Polygon
 outline=Polygon([[-97,31],[-76,34],[-73,43],[-73,72],[-76,81],[-97,81]])
 outer=prism(outline,10,20)
 # Open U-channel: broad cheek planes and one rear dorsal wall. The
 # shoulder top/output seats remain uncovered for bolt service.
 cavity=prism(Polygon([[-94,25],[-60,25],[-60,85],[-94,85]]),7.4,14.8)
 shell=outer.cut(cavity,tol=1e-5).fix()
 support=b.SHAPES['P01-shoulder-monobloc']
 for z in [44,70]:
  # Small bosses bridge the air gap: opposing faces seat on the real8mm bridge.
  for sign in [-1,1]:shell=shell.fuse(b.cyl([-85,sign*4.3,z],[0,sign,0],5.5,5.7)).fix()
  shell=b.drill(shell,[-85,-14,z],[0,1,0],3.5,28)
  support=b.drill(support,[-85,-5,z],[0,1,0],3.5,10)
  c.std_bolt(f'S01-{z}-M3',[-85,-10,z],[0,1,0],3,30,20,1)
  c.std_nut(f'S01-{z}-nut',[-85,-12.9,z],[0,1,0],3,1)
  w=b.ring([-85,-10.5,z],[0,1,0],3.5,1.7,.5)
  c.part(f'S01-{z}-nut-washer',w,1,'hardware',material='steel M3 flat washer',mass=w.Volume()*7.85e-6)
 # The original bridge remains the load path, with2 new3.5mm through-bores.
 c.part('P01-shoulder-monobloc',support,1,note='Original A10 load geometry with two D3.5 cross-bores at X-85,Z44/70 for removable shield. Strength after drilling unqualified.')
 for delta in [(0,0,0),(.3,0,0),(-.3,0,0),(0,.3,0),(0,-.3,0),(0,0,.3),(0,0,-.3)]:shell=shell.cut(support.translate(delta),tol=1e-5).fix()
 for side,y0,dy in [('front',.2,30),('rear',-30,29.8)]:
  s=shell.intersect(cq.Solid.makeBox(220,dy,100,b.V([-110,y0,10]))).fix()
  c.part('S01-shoulder-'+side,s,1,'printed_cover',note='Canted two-piece bridge shield,2.6mm nominal side skin,0.4mm centre seam. TwoM3x30 through-bolts with washers/nuts,0.3mm rigid support gap. Fit prototype; remove before motor service.')
 import refine
 refine.refine(['P01-shoulder-monobloc','S01-shoulder-front','S01-shoulder-rear'])
 D['parts']=b.PARTS;D['hardware']=c.HARDWARE
 D['changed_parts']=sorted(set(D['changed_parts']+['P01-shoulder-monobloc','S01-shoulder-front','S01-shoulder-rear']))
 (OUT/'manifest.json').write_text(json.dumps(D,ensure_ascii=False,separators=(',',':'))+'\n')
 compact={k:v for k,v in D.items() if k!='parts'};compact['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in b.PARTS]
 (OUT/'parts.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
 print('A11_SHOULDER',len(D['parts']),flush=True)
if __name__=='__main__':main()
