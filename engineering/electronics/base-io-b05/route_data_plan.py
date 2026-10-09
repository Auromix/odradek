# SPDX-License-Identifier: CC-BY-NC-4.0
"""Offline geometrical route planning from saved native pads; editor DRC is independent."""
import heapq,json,math
from pathlib import Path
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point,LineString,box,Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'reports/b06-power-reopened.json').read_text())['value']
STEP=.1; W=.24; GAP=.20
X,Y=np.meshgrid(np.arange(1,76+STEP/2,STEP),np.arange(1,55+STEP/2,STEP))
routes=[];vias=[]
regions=json.loads((ROOT/'reports/b06-data-regions.json').read_text())
keepouts=[]
for r in regions:
    nums=[a for a in r['complexPolygon']['polygon'] if isinstance(a,(int,float))]
    keepouts.append((r['layer'],Polygon([(nums[i]*.0254,-nums[i+1]*.0254) for i in range(0,len(nums),2)])))
def xy(p):return [p['x']*.0254,-p['y']*.0254]
def padshape(p):
    x,y=xy(p); return Point(x,y).buffer(max(p['pad'][1:])*.0254/2,quad_segs=24)
for l in P['lines']:
    routes.append({'net':l['net'],'layer':l['layer'],'width_mm':l['lineWidth']*.0254,
                  'points':[[l['startX']*.0254,-l['startY']*.0254],[l['endX']*.0254,-l['endY']*.0254]],'existing':True})
pairs=[(1,2),(3,6),(4,5),(7,8)]
for k,(a,b) in enumerate(pairs):
    x=26+5*k
    core=[(x+.9,40),(x+24.9,16)]
    if k==0:core=[(26.9,40),(34.9,32),(34.9,14),(48.9,14)]
    if k==3:core=[(41.9,40),(41.9,38),(44.9,35),(65.9,16)]
    for n,side in [(a,1),(b,-1)]:
        pts=list(LineString(core).offset_curve(side*(.25 if k==3 else .22),join_style=2).coords)
        start=[x+(1.8 if side==1 else 0),43]
        end=[x+24+(1.8 if side==1 else 0),13]
        if k==0:end=[50.9,17 if side==1 else 11]
        routes.append({'net':f'ETH_{n}','layer':1,'width_mm':W,'points':[start,*pts,end],'main':True})
        for point in [start,end]:vias.append({'net':f'ETH_{n}','point':point,'hole_mm':.6,'diameter_mm':1.2})
def obstacles(net,layer,for_via=False):
    objs=[]
    margin=(.6 if for_via else W/2)
    objs.extend(p.buffer(margin+.05) for lay,p in keepouts if lay==layer)
    for p in P['pads']:
        if p['net']==net and not for_via:continue
        spacing=.35 if not p['metallization'] else GAP
        objs.append(padshape(p).buffer(spacing+margin))
    for r in routes:
        if r['layer']==layer and r['net']!=net:
            spacing=1.0 if r['net'] in ['VIN48','RETURN48'] else GAP
            objs.append(LineString(r['points']).buffer(r['width_mm']/2+spacing+margin,quad_segs=12))
    for v in vias:
        if v['net']!=net or for_via:objs.append(Point(v['point']).buffer(v['diameter_mm']/2+GAP+margin,quad_segs=12))
    return unary_union(objs)
def idx(p):return (int(round((p[1]-1)/STEP)),int(round((p[0]-1)/STEP)))
def point(i):return [round(1+i[1]*STEP,4),round(1+i[0]*STEP,4)]
def route(net,start,end):
    blocked=np.array([contains_xy(obstacles(net,layer).buffer(.075),X,Y) for layer in [1,2]])
    via_blocked=contains_xy(unary_union([obstacles(net,layer,True) for layer in [1,2]]).buffer(.075),X,Y)
    s=(1,*idx(start));t=(1,*idx(end))
    # Exact endpoints are retained; only route-search samples use this grid.
    blocked[s]=False;blocked[t]=False
    todo=[(math.dist(s,t),0,s)];dist={s:0};prev={}
    moves=[(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    while todo:
        _,d,a=heapq.heappop(todo)
        if d>dist[a]+1e-8:continue
        if a==t:
            path=[a]
            while path[-1]!=s:path.append(prev[path[-1]])
            path=path[::-1]
            chunks=[];raw=[start];layer=2
            for i in range(1,len(path)):
                if path[i][0]!=path[i-1][0]:
                    p=point(path[i][1:])
                    raw.append(p);chunks.append((layer,raw));raw=[p];layer=path[i][0]+1
                    if math.dist(p,start)>.08 and math.dist(p,end)>.08:
                        vias.append({'net':net,'point':p,'hole_mm':.6,'diameter_mm':1.2,'fanout':True})
                else:raw.append(point(path[i][1:]))
            raw[-1]=end;chunks.append((layer,raw))
            out=[]
            for layer,pts in chunks:
                if len(pts)<2 or all(math.dist(pts[0],q)<1e-8 for q in pts):continue
                obs=obstacles(net,layer)
                # Greedy line-of-sight compression preserves independently checked clearance.
                compact=[pts[0]];i=0
                while i<len(pts)-1:
                    for j in range(len(pts)-1,i,-1):
                        if not LineString([pts[i],pts[j]]).intersects(obs):break
                    if j==i:raise RuntimeError('No valid simplification')
                    compact.append(pts[j]);i=j
                if LineString(compact).intersects(obs):raise RuntimeError('Grid boundary '+net)
                out.append({'net':net,'layer':layer,'width_mm':W,'points':compact,'fanout':True})
            return out
        for dy,dx in moves:
            b=(a[0],a[1]+dy,a[2]+dx)
            if not (0<=b[1]<blocked.shape[1] and 0<=b[2]<blocked.shape[2]):continue
            if blocked[b]:continue
            if dx and dy and (blocked[a[0],a[1],b[2]] or blocked[a[0],b[1],a[2]]):continue
            nd=d+math.hypot(dx,dy)
            if nd<dist.get(b,float('inf')):
                dist[b]=nd;prev[b]=a
                heapq.heappush(todo,(nd+math.dist(b,t),nd,b))
        # Layer changes are limited to the two connector fanout regions.
        if a[1:]==s[1:] or a[1:]==t[1:] or not via_blocked[a[1],a[2]]:
            b=(1-a[0],a[1],a[2]);nd=d+(0 if a[1:] in [s[1:],t[1:]] else 100)
            if not blocked[b] and nd<dist.get(b,float('inf')):
                dist[b]=nd;prev[b]=a;heapq.heappush(todo,(nd+math.dist(b,t),nd,b))
    raise RuntimeError('No bottom-layer path: '+net)
for k,(a,b) in enumerate(pairs):
    for n in [a,b]:
        net=f'ETH_{n}'
        anchors=[v['point'] for v in vias if v['net']==net]
        ps=[p for p in P['pads'] if p['net']==net]
        for prefix,anchor in [('ie48',anchors[0]),('ie8',anchors[1])]:
            pad=next(p for p in ps if p['primitiveId'].startswith(prefix))
            chunks=route(net,xy(pad),anchor)
            routes.extend(chunks)
            print(net,prefix,len(chunks),round(sum(LineString(r['points']).length for r in chunks),3),flush=True)
new=[r for r in routes if not r.get('existing')]
plan={'stage':'native DATA candidate','source':'b06-power-reopened.json','width_mm':W,'gap_mm':GAP,
      'pairs':pairs,'routes':new,'vias':list({(v['net'],tuple(v['point'])):v for v in vias}.values()),
      'length_mm':{f'ETH_{n}':sum(LineString(r['points']).length for r in new if r['net']==f'ETH_{n}')+3.2 for n in range(1,9)}}
(ROOT/'reports/b06-data-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(plan['length_mm'])
