# SPDX-License-Identifier: CC-BY-NC-4.0
"""Versioned combined audit, keeping the same bounded review implementation."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'engineering/arm_a14/link-shell01/review.py').read_text()
s=s.replace("for p in D['parts']:new.append((p,load(OUT,p['id'])))","for p in D['parts']:\n f=ROOT/p['source_step_path'];sources[str(f.relative_to(ROOT))]=sha(f);new.append((p,cq.importers.importStep(str(f)).val()))")
s=s.replace("for p in M['parts']:others.append((p,load(folder,p['id'])))","for p in M['parts']:\n  if p['id']!='A12-WR02-J6-shield-B':others.append((p,load(folder,p['id'])))")
s=s.replace("(5,[-90,0,60,130])","(5,[-90,0,60,130]),(6,[-60,-30,0,30,60]),(7,[-90,-45,45,90])")
s=s.replace('cover_count=4','cover_count=len(new)')
s=s.replace('New detachable link skins vs','New detachable link skins and trimmed J6 B guard vs')
exec(compile(s,__file__,'exec'),dict(__file__=__file__))
