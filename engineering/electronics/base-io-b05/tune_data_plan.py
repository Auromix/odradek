# SPDX-License-Identifier: CC-BY-NC-4.0
"""Length-tune a geometrical candidate without deleting keepouts or relaxing DRC.

Matching trace lengths is not an impedance or channel-compliance qualification.
"""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import LineString,box,Point,Polygon
from shapely.ops import unary_union
HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'reports/b06-data-plan.json').read_text())
p=json.loads((HERE/'reports/b06-power-reopened.json').read_text())['value']
regions=json.loads((HERE/'reports/b06-data-regions.json').read_text())
def obs(net,layer):
    geoms=[]
    for pad in p['pads']:
        if pad['net']==net:continue
        geoms.append(Point(pad['x']*.0254,-pad['y']*.0254).buffer(max(pad['pad'][1:])*.0254/2+.32))
    for r in regions:
        if r['layer']!=layer:continue
        n=[v for v in r['complexPolygon']['polygon'] if isinstance(v,(float,int))]
        geoms.append(Polygon([(n[i]*.0254,-n[i+1]*.0254) for i in range(0,len(n),2)]).buffer(.15))
    for r in plan['routes']:
        coupled=any(net in [f'ETH_{a}',f'ETH_{b}'] and r['net'] in [f'ETH_{a}',f'ETH_{b}'] for a,b in plan['pairs'])
        if r['net']!=net and r['layer']==layer:geoms.append(LineString(r['points']).buffer(.24+(.127 if coupled else .20)-.001))
    for v in plan['vias']:
        if v['net']!=net:geoms.append(Point(v['point']).buffer(.6+.20+.12))
    for l in p['lines']:
        if l['layer']==layer:geoms.append(LineString([(l['startX']*.0254,-l['startY']*.0254),(l['endX']*.0254,-l['endY']*.0254)]).buffer(l['lineWidth']*.0254/2+1+.12))
    return unary_union(geoms)
def length(net):return sum(LineString(r['points']).length for r in plan['routes'] if r['net']==net)
for a,b in plan['pairs']:
    la,lb=length(f'ETH_{a}'),length(f'ETH_{b}')
    net=f'ETH_{a if la<lb else b}';extra=abs(la-lb)
    candidates=[]
    for ri,r in enumerate(plan['routes']):
        if r['net']!=net:continue
        obstruction=obs(net,r['layer'])
        for i in range(1,len(r['points'])):
            start,end=np.array(r['points'][i-1]),np.array(r['points'][i]);d=end-start;L=np.linalg.norm(d);u=d/L
            for n in range(1,int((L-2)//2)+1):
                # Each trapezoid adds 2*sqrt(.4^2+A^2)-.8 mm.
                A=math.sqrt(((extra/n+.8)/2)**2-.4**2)
                if A>4:continue
                for sign in [-1,1]:
                    normal=np.array([-u[1],u[0]])*sign
                    offset=(L-n*2)/2
                    pts=[start.tolist()]
                    for k in range(n):
                        s=offset+2*k
                        for t,h in [(s,0),(s+.4,A),(s+1,A),(s+1.4,0),(s+2,0)]:pts.append((start+u*t+normal*h).tolist())
                    pts.append(end.tolist())
                    line=LineString(pts)
                    if line.is_simple and box(1,1,76,55).contains(line) and not line.intersects(obstruction):
                        candidates.append((0 if r.get('fanout') else 1,A,n,ri,i,pts))
    if not candidates:raise RuntimeError('No clear tuning area for '+net)
    _,amp,n,ri,i,pts=min(candidates,key=lambda c:(c[0],c[1]))
    r=plan['routes'][ri];r['points']=r['points'][:i-1]+pts+r['points'][i+1:];r['length_tuned']=True
    print(net,extra,'amplitude',amp,'count',n,'layer',r['layer'],flush=True)
plan['trace_length_mm']={f'ETH_{n}':length(f'ETH_{n}') for n in range(1,9)}
plan['via_count']={f'ETH_{n}':sum(v['net']==f'ETH_{n}' for v in plan['vias']) for n in range(1,9)}
plan['qualification']='Trace geometry only; native DRC, plane rebuild, impedance and link tests still required.'
(HERE/'reports/b06-data-tuned-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(plan['trace_length_mm'])
