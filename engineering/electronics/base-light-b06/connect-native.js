// SPDX-License-Identifier: CC-BY-NC-4.0
const nets=__CLI__.args.nets;const result={};
await eda.dmt_EditorControl.openDocument('214317e654843e43');
const components=await eda.pcb_PrimitiveComponent.getAll();
const j=components.find(p=>p.designator==='J1');
await eda.pcb_PrimitiveComponent.modify(j.primitiveId,{x:19.8/.0254,y:-10.5/.0254});
for(const c of await eda.pcb_PrimitiveComponent.getAll()){
 for(const p of await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)){
  p.setState_Net(nets[c.designator][p.padNumber]);
  // Library R0603 suppresses paste by -3937 mil; use normal zero expansion for assembly.
  p.setState_SolderMaskAndPasteMaskExpansion({topSolderMask:2,bottomSolderMask:2,topPasteMask:0,bottomPasteMask:0});
  await p.done();
 }
}
result.pcbSave=await eda.pcb_Document.save();
result.pcb=[];
for(const c of await eda.pcb_PrimitiveComponent.getAll())result.pcb.push({d:c.designator,component:c,pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)});
await eda.dmt_EditorControl.openDocument('b69e3ef370112288');
if((await eda.sch_PrimitiveWire.getAll()).length)throw Error('Schematic already wired');
for(const c of await eda.sch_PrimitiveComponent.getAll()){
 if(!nets[c.designator])continue;
 for(const p of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)){
  const net=nets[c.designator][p.pinNumber];
  let x=p.x,y=p.y,line=[x,y];
  if(c.designator==='J1' && p.pinNumber==='1'){line.push(x-30,y,x-30,y+65);x-=30;y+=65;}
  else if(c.designator==='J1' && p.pinNumber==='3'){line.push(x-50,y,x-50,y-65);x-=50;y-=65;}
  else {const rad=p.rotation*Math.PI/180;x+=40*Math.cos(rad);y+=40*Math.sin(rad);line.push(x,y);}
  if(!await eda.sch_PrimitiveWire.create(line,net))throw Error('Wire '+c.designator+'.'+p.pinNumber);
  if(!await eda.sch_PrimitiveComponent.createNetPort('BI',net,x,y,p.rotation))throw Error('Net port '+net);
 }
}
result.schSave=await eda.sch_Document.save();return result;
