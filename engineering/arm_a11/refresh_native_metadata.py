# SPDX-License-Identifier: CC-BY-NC-4.0
"""Refresh only saved source metadata, retaining exact object geometry/rig."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a11/build';p=json.loads((OUT/'metadata-correction.json').read_text())
assert bpy.context.scene['Source manifest SHA256']==p['old_manifest_sha256']
bpy.context.scene['Source manifest SHA256']=p['new_manifest_sha256']
bpy.context.scene['Metadata-only correction']='P01 added to changed-part index; geometry/rig unchanged'
for text in bpy.data.texts:
 if p['old_manifest_sha256'] in text.as_string():text.from_string(text.as_string().replace(p['old_manifest_sha256'],p['new_manifest_sha256']))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('SOURCE_METADATA_REFRESHED',bpy.data.filepath)
