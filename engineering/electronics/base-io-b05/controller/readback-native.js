// SPDX-License-Identifier: CC-BY-NC-4.0
// Invoke through official JLCEDA API in the IO PCB after saving and reopening.
// Host must persist output and SHA256 of the actual saved native source files.
const components = await eda.pcb_PrimitiveComponent.getAll();
const attached_pins = [];
for (const c of components)
  attached_pins.push(...await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId));
return {
  components, attached_pins, pads: await eda.pcb_PrimitivePad.getAll(),
  lines: await eda.pcb_PrimitiveLine.getAll(), vias: await eda.pcb_PrimitiveVia.getAll(),
  regions: await eda.pcb_PrimitiveRegion.getAll(), pours: await eda.pcb_PrimitivePour.getAll(),
  drc: await eda.pcb_Drc.check(true, false, true)
};
