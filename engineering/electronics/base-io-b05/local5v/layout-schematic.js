// SPDX-License-Identifier: CC-BY-NC-4.0
// First layout only, after create/connect. Move the mechanical placeholders to
// a compact row and keep the complete power circuit inside the drawing border.
await eda.dmt_EditorControl.openDocument('30968987fbc1647d');
const cs=await eda.sch_PrimitiveComponent.getAll();
const power={F1:[210,-420],D1:[420,-420],U1:[650,-420],C1:[420,-510],C2:[550,-510],R1:[700,-510],J7:[900,-420]};
const nets={U1:{1:'LAMP_VIN',2:'RETURN48',3:'LAMP5V'},F1:{1:'LAMP_FUSED48',2:'VIN48'},D1:{1:'LAMP_VIN',2:'LAMP_FUSED48'},C1:{1:'RETURN48',2:'LAMP_VIN'},C2:{1:'RETURN48',2:'LAMP5V'},R1:{1:'RETURN48',2:'LAMP5V'},J7:{1:'LAMP5V',2:'LAMP_PWM_RESERVED',3:'RETURN48',4:'RETURN48',5:'RETURN48'}};
const wires=await eda.sch_PrimitiveWire.getAll();
// Native wire DTO is positional; callers supply its exact verified IDs.
await eda.sch_PrimitiveWire.delete(__CLI__.args.power_wire_ids);
await eda.sch_PrimitiveComponent.delete(cs.filter(c=>c.componentType==='netport'&&c.y>=-545&&c.y<=-385).map(c=>c.primitiveId));
for(const c of cs){
 if(power[c.designator])await eda.sch_PrimitiveComponent.modify(c.primitiveId,{x:power[c.designator][0],y:power[c.designator][1],otherProperty:{...c.otherProperty}});
 if(/^H[1-6]$/.test(c.designator))await eda.sch_PrimitiveComponent.modify(c.primitiveId,{x:90+155*(Number(c.designator.slice(1))-1),y:-610,otherProperty:{...c.otherProperty,Value:"M3_NPTH"}});
}
for(const c of await eda.sch_PrimitiveComponent.getAll()){
 if(!nets[c.designator])continue;
 for(const p of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)){
  const a=p.rotation*Math.PI/180,x=p.x+35*Math.cos(a),y=p.y+35*Math.sin(a),net=nets[c.designator][p.pinNumber];
  if(!await eda.sch_PrimitiveWire.create([p.x,p.y,x,y],net))throw Error('Wire');
  if(!await eda.sch_PrimitiveComponent.createNetPort('BI',net,x,y,p.rotation))throw Error('Net');
 }
}
return {saved:await eda.sch_Document.save(),drc:await eda.sch_Drc.check(true,false,true)};
