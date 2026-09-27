# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Import a local SES if supplied, synchronize source metadata and refill GND.
Run with KiCad's bundled Python. Does not change any LED coordinates.
"""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import wx,pcbnew
app=wx.App(False)
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--ses');p.add_argument('--input',default='upper-petal.kicad_pcb');p.add_argument('--output',default='upper-petal.kicad_pcb');a=p.parse_args()
b=pcbnew.LoadBoard(str(D/a.input))
if a.ses:
 assert pcbnew.ImportSpecctraSES(b,str(D/a.ses)), 'SES import failed'
xml=ET.parse(D/'checks'/'upper-petal.xml')
comp={c.attrib['ref']:c for c in xml.findall('./components/comp')}
M=json.loads((D/'schematic-build-map.json').read_text());source=json.loads((D.parent/'netlist.json').read_text())
exp={(p['ref'],p['pin']):p['net'] for p in source['pins']}
netfromxml={}
for net in xml.findall('./nets/net'):
 for nd in net.findall('node'):netfromxml[(nd.attrib['ref'],nd.attrib['pin'])]=net.attrib['name']
for fp in b.GetFootprints():
 r=fp.GetReference();c=comp[r]
 fp.SetValue(c.findtext('value'));fp.SetFPIDAsString(c.findtext('footprint'))
 fp.SetPath(pcbnew.KIID_PATH('/'+M['root_uuid']+'/'+M['reference_uuids'][r]))
 fp.SetField('MPN',c.find("fields/field[@name='MPN']").text);fp.GetField('MPN').SetVisible(False)
 fp.SetField('Datasheet',c.findtext('datasheet'));fp.GetField('Datasheet').SetVisible(False)
 for pad in fp.Pads():
  num=pad.GetNumber()
  if not num:continue
  name=netfromxml[(r,num)]
  net=b.FindNet(name)
  if not net:
   net=pcbnew.NETINFO_ITEM(b,name);b.Add(net);net.thisown=False
  pad.SetNet(net)
# Ground is refilled around imported tracks. A 4-signal-layer trial does not
# retain a continuous GND reference; that difference must remain documented.
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/a.output),b)
print('Synchronized footprint identities, source fields, NC nets; GND refilled:',a.output)
