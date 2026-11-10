#!/usr/bin/env python3
"""Higi 0.15.193 DRY - enforce visible diagnostic and printed-source boundary."""
from pathlib import Path
import sys
root=Path(sys.argv[1]);base=root/'app/src/main/java/com/example/hebrewcrossword'
engine=base/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
if s.count(needle)!=1:raise SystemExit('Missing exact final-review boundary')
block=r'''        // V193 - final administrator-only pass. The V192 word-based
        // refinement may be unable to locate an answer-length token and
        // otherwise silently leave a five-line V178 legacy proposal on screen.
        // Here independent exact printed-number pixel anchors bound multi-line
        // previews; every decision overrides the earlier V178 diagnostic.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val before193=newPreviews.map{(candidate,g)->
                wire(candidate) to g.lines.map{p->
                    CropRect((p.left*w).roundToInt(),(p.top*h).roundToInt(),
                        (p.right*w).roundToInt(),(p.bottom*h).roundToInt())
                }
            }.toMap()
            val audit193=OcrMultiPieceBoundaryV193.inspect(
                before193,auditWords,expectedWires,w,h)
            audit193.previews.forEach{(label,parts)->
                val k=key(label)
                if(k in accepted)return@forEach
                val proposal=geometry(parts,w,h)
                val check=ClueRegionValidation.validateGeometryNormalized(
                    proposal,w,h,gridPoints)
                if(check.usable){
                    newPreviews[k]=proposal
                    newPreviewReasons[k]=audit193.diagnostics[label].orEmpty()
                } else {
                    newPreviews.remove(k)
                    newPreviewReasons[k]="V193_GEOMETRY_REJECTED:"+check.reason+
                        "; manual review; NO canonical write"
                }
            }
            audit193.withheld.forEach{(label,why)->
                val k=key(label)
                if(k !in accepted){
                    newPreviews.remove(k)
                    newPreviewReasons[k]=why
                    unresolved[k]="V193_ADMIN_REVIEW_UNSAFE_MULTIPIECE"
                }
            }
            audit193.diagnostics.forEach{(label,why)->
                val k=key(label)
                if(k !in accepted && k !in audit193.previews &&
                    k !in audit193.withheld) {
                    // Make failure visible instead of retaining stale V178
                    // diagnostics. A single inconclusive pass is not enough
                    // evidence to overwrite a preview.
                    newPreviewReasons[k]=why
                }
            }
        }
'''
s=s.replace(needle,block+needle,1)
engine.write_text(s,encoding='utf-8')
(base/'OcrMultiPieceBoundaryV193.kt').write_text(
    Path(__file__).with_name('higi-v193-boundary.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrMultiPieceBoundaryV193Test.kt'
test.write_text(Path(__file__).with_name('higi-v193-boundary-test.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for old,new in (('versionCode = 342','versionCode = 343'),
                ('versionName = "0.15.192"','versionName = "0.15.193"')):
    if t.count(old)!=1:raise SystemExit('Version invariant failed: '+old)
    t=t.replace(old,new,1)
gradle.write_text(t,encoding='utf-8')
print("Prepared Higi v193 DRY preview-only source-number boundary.")
