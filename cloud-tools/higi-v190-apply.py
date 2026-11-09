#!/usr/bin/env python3
"""Higi 0.15.190 DRY: source-word anchored reviewer, no canonical updates."""
from pathlib import Path
import sys
root=Path(sys.argv[1]);base=root/'app/src/main/java/com/example/hebrewcrossword'
engine=base/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
start=s.index('        // V189 DRY review-only safety guard.')
end=s.index('        expected.forEach{e->val k=key(e.key); if(k !in accepted)',start)
new=r'''        // V190: Review-only source-word refinement. Use physical OCR printed
        // number coordinates, not a textual diagnostic prefix (V189 regression).
        // Never move an accepted/verified crop or update canonical data.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val oldPixels=newPreviews.map{(k,g)->
                wire(k) to g.lines.map{part->
                    CropRect((part.left*w).roundToInt(),(part.top*h).roundToInt(),
                        (part.right*w).roundToInt(),(part.bottom*h).roundToInt())
                }
            }.toMap()
            val reviewed=OcrColumnSourceWordV190.review(
                oldPixels,auditWords,expectedWires,w,h)
            reviewed.previews.forEach{(label,pieces)->
                val k=key(label)
                val proposal=geometry(pieces,w,h)
                val verdict=ClueRegionValidation.validateGeometryNormalized(
                    proposal,w,h,gridPoints)
                if(verdict.usable){
                    newPreviews[k]=proposal
                    newPreviewReasons[k]=reviewed.diagnostic[label].orEmpty()
                }else{
                    newPreviews.remove(k)
                    newPreviewReasons[k]="V190_GEOMETRY_REJECTED:"+verdict.reason
                }
            }
            reviewed.withheld.forEach{(label,why)->
                val k=key(label)
                newPreviews.remove(k)
                newPreviewReasons[k]=why
            }
        }
'''
s=s[:start]+new+s[end:]
engine.write_text(s,encoding='utf-8')
(root/'app/src/main/java/com/example/hebrewcrossword/OcrColumnSourceWordV190.kt').write_text(
    Path(__file__).with_name('higi-v190-word-review.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrColumnSourceWordV190Test.kt'
test.write_text(Path(__file__).with_name('higi-v190-word-review-test.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
gradle=root/'app/build.gradle.kts';t=gradle.read_text(encoding='utf-8')
for a,b in (('versionCode = 339','versionCode = 340'),
            ('versionName = "0.15.189"','versionName = "0.15.190"')):
    if t.count(a)!=1:raise SystemExit('Version invariant failed: '+a)
    t=t.replace(a,b,1)
gradle.write_text(t,encoding='utf-8')
print('Prepared V190 DRY source word boundary review and JVM tests.')
