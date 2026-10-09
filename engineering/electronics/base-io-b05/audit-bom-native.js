// SPDX-License-Identifier: CC-BY-NC-4.0
// Read-only native verification. Open the saved IO PCB before executing.
// Do not update schematic attributes with partial otherProperty maps:
// JLCEDA replaces that map; library footprint attributes require native UUIDs.
const components=await eda.pcb_PrimitiveComponent.getAll();
const expected={J1:'615008160221',J2:'615008160221',J3:'1720466',J4:'74651173',J5:'74651173',J6:'74651173'};
if(!components.some(c=>c.primitiveId==='ie48'&&c.designator==='J1'))throw Error('Wrong PCB');
for(const c of components){
 if(/^H[1-6]$/.test(c.designator)&&c.addIntoBom!==false)throw Error('Mounting hole in BOM');
 if(expected[c.designator]&&(c.manufacturerId!==expected[c.designator]||!c.addIntoBom))throw Error('Missing physical-part MPN');
}
const drc=await eda.pcb_Drc.check(true,false,true);
if(!Array.isArray(drc)||drc.length)throw Error('Native DRC or schematic mismatch');
const f=await eda.pcb_ManufactureData.getBomFile('B06-IO-Native-BOM','csv');
if(!f)throw Error('No native BOM');
return {drc,components,bom_text:await f.text(),lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),pads:await eda.pcb_PrimitivePad.getAll()};
