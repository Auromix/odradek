#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json,xml.etree.ElementTree as E,hashlib,math
D=Path(__file__).resolve().parent
load=lambda x:json.loads((D/x).read_text());N=load('netlist.json');B=load('native-readback.json');erc=load('reports/erc.json');drc=load('reports/drc.json');T=E.parse(D/'reports/netlist.xml');c=[]
def check(name,truth,detail=None):
 c.append(dict(name=name,pass_=bool(truth),detail=detail));assert truth,(name,detail)
check('native_readback_current_sha',B['board_sha256']==hashlib.sha256((D/'kicad/base-rear-interface01.kicad_pcb').read_bytes()).hexdigest())
check('routing_replay_exact',B['tracks']==load('routing-plan.json')['tracks'] and B['vias']==load('routing-plan.json')['vias'])
check('nativeERC0',sum(len(s.get('violations',[]))for s in erc['sheets'])==0)
for k in ['violations','unconnected_items','schematic_parity','ignored_checks']:check(k+'0',len(drc[k])==0)
actual={(net.get('name'),n.get('ref'),n.get('pin'))for net in T.findall('.//nets/net')for n in net.findall('node')}
expected={(p['net'],p['ref'],p['pin'])for p in N['pins']}
check('schematicXML_exact25pins',actual==expected,[len(actual),len(expected)])
physical={(p['net'],p['ref'],p['pin'])for p in B['pads']if p['pin']}
check('nativepads_exact_logicalnets',physical==expected)
check('12realfootprints_no_router_waypoints',len(B['footprints'])==12 and all(not f['ref'].startswith('WAYPOINT')for f in B['footprints']))
# EveryEthernetnet must be one simple copper chain, not a loop or unused stub.
# Graph nodes snap1um to merge1nm legacyrouter endrounding; actual copper connectivity/clearance uses nativeDRC unchanged.
from collections import defaultdict
for n in ['ETH_'+str(i)for i in range(1,9)]:
 adj=defaultdict(set);edges=[]
 def node(xy,ly):return (round(xy[0],3),round(xy[1],3),ly)
 for t in B['tracks']:
  if t['net']!=n:continue
  a=node(t['start_uv_mm'],t['layer']);b=node(t['end_uv_mm'],t['layer']);adj[a].add(b);adj[b].add(a);edges.append((a,b))
 for v in B['vias']:
  if v['net']!=n:continue
  a=node(v['uv_mm'],'F.Cu');b=node(v['uv_mm'],'B.Cu');adj[a].add(b);adj[b].add(a);edges.append((a,b))
 seen=set();todo=[next(iter(adj))]
 while todo:
  a=todo.pop()
  if a in seen:continue
  seen.add(a);todo+=list(adj[a]-seen)
 ends=[k for k,v in adj.items()if len(v)==1]
 expectedends={tuple(round(x,3)for x in p['uv_mm'])for p in B['pads']if p['net']==n}
 check(n+'_simple_chain',len(seen)==len(adj)and len(edges)==len(adj)-1 and len(ends)==2 and all(len(v)<=2 for v in adj.values())and {k[:2]for k in ends}==expectedends)
check('fourmount_holes',all(any(p['type']=='NPTH'and p['ref']=='H'+str(i+1)and p['uv_mm']==xy and p['drill_mm']==[3.2,3.2]for p in B['pads'])for i,xy in enumerate([[6,6],[110,6],[110,50],[6,50]])))
check('innerlayers_no_signaltracks',B['inner_track_count']==0)
check('boardthickness1.6',abs(B['thickness_mm']-1.6)<1e-8)
check('powerreturn_not_chassis',next(p['net']for p in N['pins']if p['ref']=='J5')=='RETURN48')
check('RJidentity_all8',all(sorted((p['ref'],p['pin'])for p in N['pins']if p['net']=='ETH_'+str(i))==[('J1',str(i)),('J2',str(i))]for i in range(1,9)))
check('six_native_mountkeepouts',len(B['mount_keepouts'])==6 and all(all(k.values())for k in B['mount_keepouts']))
V=load('mechanical/verification.json');P=load('mechanical/parts.json');check('all59originalsolidsvalid',V['valid']and V['parts']==59 and len(P['parts'])==59)
# Conservative materialgeometry F-side cap; excludes unverified matingplugs/wires.
check('currentmodelFside_beforeYminus3',max(p['bbox_global'][1][1]for p in P['parts'])<-3)
files={str(f.relative_to(D)):hashlib.sha256(f.read_bytes()).hexdigest()for f in D.rglob('*')if f.is_file()and f.suffix not in['.pyc','.kicad_prl','.lck']and f not in[D/'verification.json',D/'manifest.json']and '__pycache__'not in str(f)}
out=dict(revision='BRI01',passed=True,checks=c,native_checks='all severities; schematicparity; alltrackerrors; noexclusions',qualification='Reviewcandidate only. No channel/thermal/mechanicalfit qualification.',limitations=['fanout impendances and intrapairdelay not hardwaretested','power10A/20A are testtargets; pulse durationundefined','internalplug matedinsertion and crimp qualification pending','powerplug engagement offset and terminal lug geometry pending','coax ledge bend relief/manufacturingdetails and cable assemblies pending'])
(D/'verification.json').write_text(json.dumps(out,indent=2)+'\n');(D/'manifest.json').write_text(json.dumps(dict(revision='BRI01',files=files),indent=2)+'\n');print('PASS',len(c),'checks')
