# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent audit of saved/reopened native JLCEDA power copper; not a rating."""
import hashlib, heapq, json, math
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parent
before=json.loads((ROOT/'reports/b06-power-before.json').read_text())['value']
after=json.loads((ROOT/'reports/b06-power-reopened.json').read_text())['value']
assert before['rules']==after['rules'], 'DRC rules changed'
assert before['pads']==after['pads'], 'Pad geometry/net mapping changed'
lines=after['lines']
pads=after['pads']
assert len(lines)==34 and set(l['layer'] for l in lines)=={1,2}
assert set(l['net'] for l in lines)=={'VIN48','RETURN48'}
assert all(abs(l['lineWidth']*.0254-2.4)<1e-6 for l in lines)
def layer_geometry(layer):
    return sorted((l['net'],l['startX'],l['startY'],l['endX'],l['endY'],l['lineWidth'])
                  for l in lines if l['layer']==layer)
assert layer_geometry(1)==layer_geometry(2), 'Top/bottom routes differ'
def xy(x,y):return (x*.0254,-y*.0254)
def endpoints(l):return xy(l['startX'],l['startY']),xy(l['endX'],l['endY'])
polys={}
coverage={}
lengths={}
for net in ['VIN48','RETURN48']:
    group=[p for p in pads if p['net']==net]
    assert len(group)==7
    for layer in [1,2]:
        tracks=[l for l in lines if l['net']==net and l['layer']==layer]
        copper=[LineString(endpoints(l)).buffer(l['lineWidth']*.0254/2,quad_segs=64) for l in tracks]
        # All power pads are round PTH. This is outer copper geometry, not barrel resistance.
        assert all(p['pad'][0]=='ELLIPSE' and p['pad'][1]==p['pad'][2] for p in group)
        copper += [Point(xy(p['x'],p['y'])).buffer(p['pad'][1]*.0254/2,quad_segs=64) for p in group]
        region=unary_union(copper)
        assert region.geom_type=='Polygon', (net,layer,'Disconnected power copper')
        assert all(region.covers(Point(xy(p['x'],p['y']))) for p in group)
        polys[net,layer]=region
        coverage[f'{net}/L{layer}']={'pad_count':len(group),'one_connected_region':True}
    # Centerline graph shortest route between distal header tail and any stud pad.
    # Explicitly excludes pad spreading, barrels and terminals.
    graph={}
    for l in [l for l in lines if l['net']==net and l['layer']==1]:
        a,b=endpoints(l); a=tuple(round(v,4) for v in a);b=tuple(round(v,4) for v in b)
        graph.setdefault(a,[]).append((b,math.dist(a,b)))
        graph.setdefault(b,[]).append((a,math.dist(a,b)))
    start=next(p for p in group if p['primitiveId']==('ie0ie4' if net=='VIN48' else 'ie0ie7'))
    start=tuple(round(v,4) for v in xy(start['x'],start['y']))
    goalprefix='ie64' if net=='VIN48' else 'ie56'
    goals={tuple(round(v,4) for v in xy(p['x'],p['y'])) for p in group if p['primitiveId'].startswith(goalprefix)}
    distances={start:0};todo=[(0,start)]
    while todo:
        d,a=heapq.heappop(todo)
        if d>distances[a]+1e-8:continue
        for b,w in graph[a]:
            nd=d+w
            if nd<distances.get(b,float('inf')):distances[b]=nd;heapq.heappush(todo,(nd,b))
    lengths[net]=min(distances.get(g,float('inf')) for g in goals)
    assert math.isfinite(lengths[net])
gaps=[polys['VIN48',layer].distance(polys['RETURN48',layer]) for layer in [1,2]]
assert min(gaps)>1, 'Less than design review floor of 1 mm between DC poles'
loop=sum(lengths.values())*.001
resistance=1.724e-8*loop/(2*2.4e-3*35e-6)
report={
 'stage':'B06 native power routing only','date':'2026-10-09',
 'rules_unchanged':True,'pads_unchanged':True,'native_line_count':34,
 'width_per_outer_layer_mm':2.4,'top_bottom_geometry_equal':True,'power_pad_coverage':coverage,
 'DC_pole_outer_copper_min_gap_mm':min(gaps),
 'centerline_header_to_nearest_stud_mm':lengths,
 'estimate':{'assumed_outer_copper_um':35,'assumed_equal_current_share':True,
 'copper_resistivity_ohm_m':1.724e-8,'trace_loop_resistance_ohm':resistance,
 'at_10A':{'drop_V':10*resistance,'loss_W':100*resistance},
 'at_20A':{'drop_V':20*resistance,'loss_W':400*resistance},
 'exclusions':['pad spreading','PTH barrels','connector/contact resistance','wire/lug resistance','temperature coefficient','unequal sharing'],
 'is_current_rating':False},
 'native_drc':[{'name':x['name'],'count':x['count']} for x in after['drc']],
 'release':'NOT FOR FABRICATION OR POWER-UP',
 'remaining':['RJ45 differential routing','native physical stack not read back','impedance qualification','thermal/current test','actual plug/latch/cable fit'],
 'pcb_sha256':hashlib.sha256((ROOT/'base-io-b05/pcb/base-rear-interface01.epcb2').read_bytes()).hexdigest(),
 'readback_sha256':hashlib.sha256((ROOT/'reports/b06-power-reopened.json').read_bytes()).hexdigest()
}
(ROOT/'reports/b06-power-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
