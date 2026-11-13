#!/usr/bin/env python3
"""Prepare child-scoped Canonical image-swap rules, review only (no deployment).
The only changes are direct child .write rules below canonicalPuzzles/$puzzleKey.
Existing parent .write and all other Firebase rule branches are untouched.
"""
import json,sys
from pathlib import Path

p=Path(sys.argv[1])
out=Path(sys.argv[2])
data=json.loads(p.read_text())
node=data["rules"]["canonicalPuzzles"]["$puzzleKey"]
admin="(auth.uid === 'a2VsnWPc7TdeyCHltiunJoBcevB3' || root.child('adminUsers').child(auth.uid).val() === true || root.child('adminUsers').child(auth.uid).child('role').val() === 'admin' || root.child('adminUsers').child(auth.uid).child('role').val() === 'superadmin')"
rootGuard=f"auth != null && {admin} && data.parent().child('schema').val() === 1 && data.parent().child('parserSchema').val() === 2 && data.parent().child('issueKey').isString() && data.parent().child('gridSignature').isString()"
urlOld="data.parent().child('sourceImageUrl').val()"
urlNew="newData.parent().child('sourceImageUrl').val()"
revOld="data.parent().child('revision').val()"
revNew="newData.parent().child('revision').val()"
urlChanged=f"({urlNew} !== {urlOld})"
revisionGuard=f"{revNew} === {revOld} + 1"
base=f"{rootGuard} && {urlChanged} && {revisionGuard}"
managedUrl="newData.isString() && newData.val().length <= 2500 && newData.val().matches(/^https:\\/\\/firebasestorage\\.googleapis\\.com\\/v0\\/b\\/[A-Za-z0-9._-]+\\/o\\/higi%2Fcanonical-sources%2Fv1%2F[0-9a-f]{64}%2F[0-9a-f]{64}\\.png\\?alt=media(&token=[A-Za-z0-9._-]+)?$/)"
rules={
 "sourceImageUrl":f"{base} && {managedUrl}",
 "revision":f"{base} && newData.isNumber() && newData.val() === data.val()+1",
 "updatedAt":f"{base} && newData.isNumber() && newData.val() >= now - 15000 && newData.val() <= now + 15000",
 "lastEditedBy":f"{base} && newData.val() === auth.uid",
 "lastEditedByName":f"{base} && newData.isString() && newData.val().length <= 40",
 "clueRegionsRevision":f"{base} && newData.isNumber() && newData.val() === {revNew}",
}
for field in ["clueRegions","clueRegionLines","clueRegionEvidence","clueRegionEdits","clueApprovals"]:
 rules[field]=f"{base} && !newData.exists()"
for field,rule in rules.items():
 branch=node.setdefault(field,{})
 if ".write" in branch: raise RuntimeError(f"Do not override existing child write: {field}")
 branch[".write"]=rule
# Record expected unchanged parent write; deny all parent transaction image changes.
assert node[".write"] == json.loads(p.read_text())["rules"]["canonicalPuzzles"]["$puzzleKey"][".write"]
out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print("PREPARED REVIEW ONLY - child write branches:",len(rules))
