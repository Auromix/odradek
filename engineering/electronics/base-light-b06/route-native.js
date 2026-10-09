// SPDX-License-Identifier: CC-BY-NC-4.0
await eda.dmt_EditorControl.openDocument('214317e654843e43');
if((await eda.pcb_PrimitiveLine.getAll()).some(x=>x.net))throw Error('Light board already routed');
for(const v of __CLI__.args.vias){
 if(!await eda.pcb_PrimitiveVia.create(v.net,v.point[0]/.0254,-v.point[1]/.0254,v.hole_mm/.0254,v.diameter_mm/.0254))throw Error('Via '+v.net);
}
for(const r of __CLI__.args.routes){
 for(let i=1;i<r.points.length;i++){
  const a=r.points[i-1],b=r.points[i];
  if(!await eda.pcb_PrimitiveLine.create(r.net,r.layer,a[0]/.0254,-a[1]/.0254,b[0]/.0254,-b[1]/.0254,r.width_mm/.0254,false))throw Error('Line '+r.net);
 }
}
const saved=await eda.pcb_Document.save();
return {saved,drc:await eda.pcb_Drc.check(true,false,true),lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll()};
