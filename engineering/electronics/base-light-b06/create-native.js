// SPDX-License-Identifier: CC-BY-NC-4.0
// Run through official extension API; coordinates in mil, local u/v millimetres.
const PCB='214317e654843e43', SCH='b69e3ef370112288';
const lib='0819f05c4eef4c71ace90d822a990e87';
const specs=[
['LED1','6d2ee854797c4e55a1a0aae2fffc2093',13,3.5,0,400,700],
['LED2','6d2ee854797c4e55a1a0aae2fffc2093',25,3.5,0,700,700],
['LED3','6d2ee854797c4e55a1a0aae2fffc2093',37,3.5,0,1000,700],
['R1','6c99a12205b44699beb7151c38669aad',13,6.5,90,400,850],
['R2','6c99a12205b44699beb7151c38669aad',25,6.5,90,700,850],
['R3','6c99a12205b44699beb7151c38669aad',37,6.5,90,1000,850],
['R4','3a88329dfeba4ae2b7e97c1498192bee',26,8.5,0,600,400],
['R5','6a676f819e3646c8b3b03380076e4c20',33,8.5,0,850,400],
['Q1','224cb8c3f814442faeca99a715e6b8a1',31,5,0,850,550],
['D1','40f5d51fb9a5496d922537e2ee8f0855',5,8,0,400,400],
['J1','fa20194ac1624d79b3182946f68bae4b',19.8,10.5,0,180,450],
['C1','3bd39859af694505ab6fccd091e26d04',6,1.5,0,600,550]
];
await eda.dmt_EditorControl.openDocument(PCB);
if((await eda.pcb_PrimitiveComponent.getAll()).length)throw Error('Refuse to duplicate populated light PCB');
const out={pcb:[],sch:[]};
for(const [d,id,u,v,r] of specs){
 const p=await eda.pcb_PrimitiveComponent.create({libraryUuid:lib,uuid:id},1,u/.0254,-v/.0254,r,false);
 if(!p)throw Error('Create PCB '+d);
 await eda.pcb_PrimitiveComponent.modify(p.primitiveId,{designator:d,uniqueId:'B06LIGHT-'+d});
 out.pcb.push({d,component:await eda.pcb_PrimitiveComponent.get(p.primitiveId),pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(p.primitiveId)});
}
const poly=await eda.pcb_MathPolygon.createPolygon(['R',0,0,50/.0254,14/.0254,0,0]);
await eda.pcb_PrimitivePolyline.create('',11,poly,.05/.0254,false);
for(const [n,u,v,d] of [['H1',2,5,2.4],['H2',48,5,2.4],['H3',8,4,3.2],['H4',42,4,3.2]]){
 await eda.pcb_PrimitivePad.create(12,n,u/.0254,-v/.0254,0,['ELLIPSE',d/.0254,d/.0254],'',['ROUND',d/.0254],0,0,0,false);
}
out.pcbSave=await eda.pcb_Document.save();
await eda.dmt_EditorControl.openDocument(SCH);
if((await eda.sch_PrimitiveComponent.getAll()).filter(x=>x.designator).length)throw Error('Refuse to duplicate populated light schematic');
for(const [d,id,u,v,r,x,y] of specs){
 const p=await eda.sch_PrimitiveComponent.create({libraryUuid:lib,uuid:id},x,y,undefined,0,false,true,true);
 if(!p)throw Error('Create SCH '+d);
 await eda.sch_PrimitiveComponent.modify(p.primitiveId,{designator:d,uniqueId:'B06LIGHT-'+d});
 out.sch.push({d,component:await eda.sch_PrimitiveComponent.get(p.primitiveId),pins:await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(p.primitiveId)});
}
out.schSave=await eda.sch_Document.save();
return out;
