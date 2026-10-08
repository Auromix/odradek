import bpy,bmesh
for name in ('B05-301-ARMOR-L','B05-301-ARMOR-R'):
 bm=bmesh.new(); bm.from_mesh(bpy.data.objects[name].data); unseen=set(bm.faces); comps=[]
 while unseen:
  f=unseen.pop(); c={f}; todo=[f]
  while todo:
   a=todo.pop()
   for e in a.edges:
    if len(e.link_faces)!=2: continue
    for g in e.link_faces:
     if g in unseen: unseen.remove(g); c.add(g); todo.append(g)
  comps.append(c)
 print(name,'FRAGMENTS',[(len(c),len({v for f in c for v in f.verts})) for c in comps])
 for c in comps:
  if len(c)<10:
   o=next(iter(c)).verts[0].co
   vol=sum((f.verts[0].co-o).dot((f.verts[1].co-o).cross(f.verts[2].co-o))/6 for f in c)*1e9
   print('SMALL',len(c),vol,[list(v.co*1000) for v in {v for f in c for v in f.verts}])
 bm.free()
