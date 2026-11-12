#!/usr/bin/env python3
"""Fail-closed v199 DRY-only source review integration on exact v198 code.
Requires two pure Kotlin resources in this same cloud-tools directory.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
assets=Path(__file__).resolve().parent
app=root/'app/src/main/java/com/example/hebrewcrossword'
tests=root/'app/src/test/java/com/example/hebrewcrossword'

for name, dest in [
    ('OcrWeeklySourceAnchorsV199.kt',app/'OcrWeeklySourceAnchorsV199.kt'),
    ('OcrWeeklySourceAnchorsV199Test.kt',tests/'OcrWeeklySourceAnchorsV199Test.kt')]:
    assert (assets/name).is_file(), f'Missing {assets/name}'
    assert not dest.exists(), f'Unexpected pre-existing {dest}'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes((assets/name).read_bytes())
    print('CREATE',dest.relative_to(root))

engine=app/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
assert s.count(needle)==1, 'HigiLocalOcrCropEngine end-of-review anchor changed'
block='''        // V199 - Yedioth Dekel WEEKLY ONLY.  Never touches `accepted` or any
        // stored/manual/canonical coordinates.  Independently reconstruct from
        // printed WORD anchors, even when V184 rejected the legacy V1 geometry.
        if(refineSharedRows && layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&
            auditWords.isNotEmpty()) {
            val independent=OcrWeeklySourceAnchorsV199.inspect(auditWords,expectedWires,w,h)
            val freshKeys=linkedSetOf<String>()
            independent.previews.forEach{(label,pieces)->
                val k=key(label)
                val proposed=geometry(pieces,w,h)
                val valid=ClueRegionValidation.validateGeometryNormalized(
                    proposed,w,h,gridPoints)
                val legacyCount=newPreviews[k]?.lines?.size ?: 0
                val shortRegression=legacyCount in 2..3 && pieces.size==1
                if(valid.usable && !shortRegression){
                    newPreviews[k]=proposed
                    newPreviewReasons[k]=independent.reasons[label].orEmpty()
                    freshKeys+=label
                    DebugLog.i("LOCAL_OCR_V199", "key=$label independent=true " +
                        "parts=${pieces.size} DRY_ONLY noCanonicalWrite=true")
                }else if(shortRegression){
                    // A single newly recognized row must not replace an older
                    // multi-piece preview without demonstrated completeness.
                    newPreviewReasons.putIfAbsent(k,
                        "V199_SINGLE_ROW_CANNOT_REPLACE_MULTILINE_REVIEW; old preview retained")
                }else{
                    newPreviewReasons[k]="V199_GEOMETRY_REJECTED:${valid.reason}; no Canonical write"
                }
            }
            independent.reasons.forEach{(label,diagnostic)->
                val k=key(label)
                if(k !in newPreviews)newPreviewReasons.putIfAbsent(k,diagnostic)
            }
            // Compare all same-direction clues, not just segments within each
            // individual clue.  Also include previous accepted proposals.
            fun asPixels(g:ClueGeometry)=g.lines.map{box->CropRect(
                (box.left*w).roundToInt(),(box.top*h).roundToInt(),
                (box.right*w).roundToInt(),(box.bottom*h).roundToInt())}
            val allPixels=linkedMapOf<String,List<CropRect>>()
            allPixels.putAll(acceptedPixels())
            newPreviews.forEach{(k,g)->allPixels[wire(k)]=asPixels(g)}
            val conflicts=OcrWeeklySourceAnchorsV199.conflictingKeys(allPixels,auditWords)
            val removed=linkedSetOf<String>()
            fun score(label:String):Int {
                val parts=allPixels[label].orEmpty()
                return (if(OcrWeeklySourceAnchorsV199.ownsPrintedNumber(
                    label,parts,auditWords))10 else 0) +
                    (if(label in freshKeys)2 else 0)
            }
            // Resolve each edge deterministically. If both competing proposals
            // have equal evidence, neither can claim ownership; both are hidden.
            conflicts.forEach{(label,neighbors)->
                neighbors.filter{label<it}.forEach{other->
                    val a=score(label);val b=score(other)
                    if(a>b)removed+=other
                    else if(b>a)removed+=label
                    else {removed+=label;removed+=other}
                }
            }
            // A rejected internal `accepted` candidate is also barred from
            // LocalOcrCropPass's legacy fallback preview for this DRY review.
            removed.forEach{label->
                val k=key(label)
                newPreviews.remove(k)
                val peers=conflicts[label].orEmpty().sorted().joinToString(",")
                val why="V199_CROSS_CLUE_OVERLAP:$peers; duplicate OCR pixels; manual review"
                newPreviewReasons[k]=why
                unresolved[k]=why
                DebugLog.w("LOCAL_OCR_V199","key=$label reason=$why")
            }
            // Ensure no remaining preview overlap after arbitration; if a
            // connected graph is still ambiguous, fail closed for all members.
            val remaining=newPreviews.map{(k,g)->wire(k) to asPixels(g)}.toMap()
            val still=OcrWeeklySourceAnchorsV199.conflictingKeys(remaining,auditWords)
            still.forEach{(label,peers)->
                val k=key(label)
                newPreviews.remove(k)
                val why="V199_CROSS_CLUE_OVERLAP:${peers.sorted().joinToString(",")}; not approved"
                newPreviewReasons[k]=why
                unresolved[k]=why
            }
        }
'''
assert block.count('OcrSeriesProfilesV197.WEEKLY.id')==1
s=s.replace(needle,block+needle,1)
engine.write_text(s,encoding='utf-8')
print('MODIFY',engine.relative_to(root))

# The fallback reviewer must not re-introduce an overlapping legacy candidate
# just removed by the global ownership arbitration.  Only the new explicit
# V199 conflict string invokes this guard; all other series remain unchanged.
path=app/'LocalOcrCropPass.kt'
s=path.read_text(encoding='utf-8')
needle='''if(key in expected && key !in verified && key !in previews &&'''
assert s.count(needle)==1, 'LocalOcrCropPass legacy preview fallback changed'
s=s.replace(needle,'''if(key in expected && key !in verified && key !in previews &&
                    detected?.review?.get(key)?.contains("V199_CROSS_CLUE_OVERLAP")!=true &&''',1)
path.write_text(s,encoding='utf-8')
print('MODIFY',path.relative_to(root))

# Update local app version only; use the existing sync script for other version
# metadata. Do NOT touch backend database/rules/deployments.
gradle=root/'app/build.gradle.kts'
s=gradle.read_text(encoding='utf-8')
for old,new in [('versionCode = 348','versionCode = 349'),
                ('versionName = "0.15.198"','versionName = "0.15.199"')]:
    assert s.count(old)==1, f'Unexpected previous version or duplicate: {old}'
    s=s.replace(old,new,1)
gradle.write_text(s,encoding='utf-8')
print('V199_DRY_SOURCE_APPLIED')