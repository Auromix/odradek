// SPDX-License-Identifier: CC-BY-NC-4.0
const PCB='52caa9452ee66dee',SCH='30968987fbc1647d';
const nets={U1:{1:'LAMP_VIN',2:'RETURN48',3:'LAMP5V'},
 F1:{1:'LAMP_FUSED48',2:'VIN48'},D1:{1:'LAMP_VIN',2:'LAMP_FUSED48'},
 C1:{1:'RETURN48',2:'LAMP_VIN'},C2:{1:'RETURN48',2:'LAMP5V'},
 R1:{1:'RETURN48',2:'LAMP5V'},J7:{1:'LAMP5V',2:'LAMP_PWM_RESERVED',3:'RETURN48',4:'RETURN48',5:'RETURN48'}};
await eda.dmt_EditorControl.openDocument(PCB);
const cs=await eda.pcb_PrimitiveComponent.getAll();
if(!cs.some(c=>c.uniqueId==='B06LOCAL5V-U1'))throw Error('Wrong PCB');
for(const c of cs){if(!nets[c.designator])continue;
 for(const p of await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)){
  if(!nets[c.designator][p.padNumber])throw Error('Unknown pad');
  p.setState_Net(nets[c.designator][p.padNumber]);
  // Do not edit attached U1 holes here: such edits can disappear on reopen.
  // The saved project-local footprint defines 1.10mm PTH / 1.60mm lands.
  await p.done();
 }
}
const pcbSave=await eda.pcb_Document.save();
await eda.dmt_EditorControl.openDocument(SCH);
for(const c of await eda.sch_PrimitiveComponent.getAll()){
 if(!nets[c.designator])continue;
 for(const p of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)){
  const net=nets[c.designator][p.pinNumber];if(!net)throw Error('Unknown pin');
  const a=p.rotation*Math.PI/180,x=p.x+35*Math.cos(a),y=p.y+35*Math.sin(a);
  if(!await eda.sch_PrimitiveWire.create([p.x,p.y,x,y],net))throw Error('Wire');
  if(!await eda.sch_PrimitiveComponent.createNetPort('BI',net,x,y,p.rotation))throw Error('Net port');
 }
}
return {pcbSave,schSave:await eda.sch_Document.save(),schDrc:await eda.sch_Drc.check(true,false,true)};
