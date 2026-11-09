#!/usr/bin/env python3
"""V192 DRY: refine legacy MULTI-PIECE OCR candidates from source-word geometry."""
from pathlib import Path
import sys
root=Path(sys.argv[1]);base=root/'app/src/main/java/com/example/hebrewcrossword'
engine=base/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
needle='''        // V191: Independent DRY administrator preview audit.'''
if s.count(needle)!=1:raise SystemExit('Expected v191 preview audit boundary missing')
block=r'''        // V192: Before the V191 safety audit, try source-word anchored
        // refinement of narrow RTL column previews, INCLUDING multi-piece
        // V178 fallbacks that V190/V191 skipped. This is only an administrator
        // preview; accepted/canonical and verified/manual crops are untouched.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val oldPreviewPixels=newPreviews.map{(candidate,g)->
                wire(candidate) to g.lines.map{part->
                    CropRect((part.left*w).roundToInt(),(part.top*h).roundToInt(),
                        (part.right*w).roundToInt(),(part.bottom*h).roundToInt())
                }
            }.toMap()
            val v192=OcrColumnBoundaryV192.review(
                oldPreviewPixels,auditWords,expectedWires,w,h)
            v192.previews.forEach{(label,pieces)->
                val k=key(label)
                if(k in accepted)return@forEach
                val proposed=geometry(pieces,w,h)
                val verdict=ClueRegionValidation.validateGeometryNormalized(
                    proposed,w,h,gridPoints)
                if(verdict.usable){
                    newPreviews[k]=proposed
                    newPreviewReasons[k]=v192.diagnostics[label].orEmpty()
                }else{
                    newPreviewReasons[k]="V192_GEOMETRY_REJECTED:"+verdict.reason
                }
            }
            v192.withheld.forEach{(label,why)->
                val k=key(label)
                if(k !in accepted){
                    newPreviews.remove(k)
                    newPreviewReasons[k]=why
                }
            }
            v192.diagnostics.forEach{(label,why)->
                val k=key(label)
                if(k !in accepted && k !in newPreviewReasons)
                    newPreviewReasons[k]=why
            }
        }
'''
s=s.replace(needle,block+needle,1)
engine.write_text(s,encoding='utf-8')
(base/'OcrColumnBoundaryV192.kt').write_text(
    Path(__file__).with_name('higi-v192-column.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrColumnBoundaryV192Test.kt'
test.write_text(Path(__file__).with_name('higi-v192-column-test.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for old,new in (('versionCode = 341','versionCode = 342'),
                ('versionName = "0.15.191"','versionName = "0.15.192"')):
    if t.count(old)!=1:raise SystemExit('Version invariant failed: '+old)
    t=t.replace(old,new,1)
gradle.write_text(t,encoding='utf-8')
print("Prepared Higi v192: multi-piece RTL word-boundary DRY reviewer.")
