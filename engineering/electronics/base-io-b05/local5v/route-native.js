// SPDX-License-Identifier: CC-BY-NC-4.0
await eda.dmt_EditorControl.openDocument('52caa9452ee66dee');
const old=await eda.pcb_PrimitiveLine.getAll();
if(old.length!==217 || old.some(l=>l.net?.startsWith('LAMP')))throw Error('Wrong source or supply already routed');
if((await eda.pcb_PrimitiveVia.getAll()).length!==16)throw Error('Unexpected existing vias');
for(const v of __CLI__.args.vias){
 if(!await eda.pcb_PrimitiveVia.create(v.net,v.point[0]/.0254,-v.point[1]/.0254,v.hole_mm/.0254,v.diameter_mm/.0254))throw Error('Via');
}
for(const r of __CLI__.args.routes){
 for(let i=1;i<r.points.length;i++){
  const a=r.points[i-1],b=r.points[i];
  if(!await eda.pcb_PrimitiveLine.create(r.net,r.layer,a[0]/.0254,-a[1]/.0254,b[0]/.0254,-b[1]/.0254,r.width_mm/.0254,false))throw Error('Route '+r.net);
 }
}
return {saved:await eda.pcb_Document.save(),drc:await eda.pcb_Drc.check(true,false,true)};
