# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Remove native-reported unused tracks/vias, never suppress a DRC rule.
Require zero missing connections before and after each cleanup iteration.
"""
import argparse,json,subprocess,hashlib,shutil
from pathlib import Path
import wx,pcbnew
app=wx.App(False);D=Path(__import__("sys").argv.pop(1)).resolve()
p=argparse.ArgumentParser();p.add_argument('--kicad-cli',required=True);a=p.parse_args();src='petal.kicad_pcb';records=[]
for cycle in range(10):
 report=D/'checks'/f'cleanup-{cycle}-drc.json'
 r=subprocess.run([a.kicad_cli,'pcb','drc','--format','json','-o',str(report),src],cwd=D,capture_output=True,text=True);assert r.returncode==0,r.stderr
 j=json.loads(report.read_text());assert not j['unconnected_items'],j['unconnected_items']
 bad=[v for v in j['violations'] if v['type'] not in ['via_dangling','track_dangling']];assert not bad,bad
 if not j['violations']:break
 uuids={item['uuid'] for v in j['violations'] for item in v['items']};b=pcbnew.LoadBoard(str(D/src));removed=[]
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString() in uuids:
   removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'kind':'via' if isinstance(t,pcbnew.PCB_VIA) else 'track'});b.Remove(t);t.thisown=False
 assert len(removed)==len(uuids),(len(removed),len(uuids))
 records.append({'cycle':cycle,'removed':removed});b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/src),b)
else:raise RuntimeError('Cleanup did not converge')

(D/'checks/cleanup-evidence.json').write_text(json.dumps({'method':'remove only native-reported dangling tracks/vias; each iteration required zero geometry errors and zero missing connections; no waived rules','rounds':records,'final_native_drc':str(report.relative_to(D)),'final_counts':{k:len(j[k]) for k in ['violations','unconnected_items','schematic_parity']},'board_sha256':hashlib.sha256((D/'petal.kicad_pcb').read_bytes()).hexdigest()},indent=2)+'\n')
print('Cleanup rounds',len(records),'all native final counts zero')
