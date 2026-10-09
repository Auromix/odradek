// SPDX-License-Identifier: CC-BY-NC-4.0
await eda.dmt_EditorControl.openDocument('52caa9452ee66dee');
const prior=await eda.pcb_PrimitiveLine.getAll();const priorVia=await eda.pcb_PrimitiveVia.getAll();
if(prior.some(x=>x.net.startsWith('ETH_'))||priorVia.length)throw Error('DATA geometry exists');
const made=[];
try{
for(const v of __CLI__.args.vias){const p=await eda.pcb_PrimitiveVia.create(v.net,v.point[0]/.0254,-v.point[1]/.0254,v.hole_mm/.0254,v.diameter_mm/.0254);if(!p)throw Error('Via creation failed');made.push(p.primitiveId);}
for(const r of __CLI__.args.routes)for(let i=1;i<r.points.length;i++){
 const a=r.points[i-1],b=r.points[i];if(Math.hypot(a[0]-b[0],a[1]-b[1])<1e-8)continue;
 if(!await eda.pcb_PrimitiveLine.create(r.net,r.layer,a[0]/.0254,-a[1]/.0254,b[0]/.0254,-b[1]/.0254,r.width_mm/.0254,false))throw Error('Line creation failed');
}
for(const [a,b] of __CLI__.args.pairs)await eda.pcb_Drc.createDifferentialPair('DATA_'+a+'_'+b,'ETH_'+a,'ETH_'+b);
await eda.pcb_PrimitiveString.modify('ie98',{text:'B06 IO / ROUTE REVIEW'});
if(!await eda.pcb_Document.save())throw Error('Save failed');
return {saved:true,lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),pairs:await eda.pcb_Drc.getAllDifferentialPairs(),drc:await eda.pcb_Drc.check(true,false,true)};
}catch(err){
 await eda.pcb_PrimitiveLine.delete((await eda.pcb_PrimitiveLine.getAll()).filter(x=>x.net.startsWith('ETH_')).map(x=>x.primitiveId));
 await eda.pcb_PrimitiveVia.delete(made); await eda.pcb_Document.save();throw err;
}
