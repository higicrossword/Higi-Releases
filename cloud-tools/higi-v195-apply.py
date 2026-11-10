#!/usr/bin/env python3
"""Higi v195: independent pixel-anchor preview using existing OCR only."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
base=root/'app/src/main/java/com/example/hebrewcrossword'
src=base/'HigiLocalOcrCropEngine.kt'
s=src.read_text(encoding='utf-8')
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
if s.count(needle)!=1:
    raise SystemExit('V195 fail closed: exact review insertion point missing')
block=r'''        // V195: Reconstruct compact RTL preview boundaries directly from the
        // existing OCR pixel rows and word boxes. This runs after V194, so
        // stale legacy V178 five-row candidates can be replaced for admin
        // inspection without touching trusted or canonical clue geometry.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val before195=newPreviews.map{(candidate,g)->
                wire(candidate) to g.lines.map{p->
                    CropRect((p.left*w).roundToInt(),(p.top*h).roundToInt(),
                        (p.right*w).roundToInt(),(p.bottom*h).roundToInt())
                }
            }.toMap()
            val v195=OcrIndependentBoundaryV195.inspect(
                before195,lines,auditWords,expectedWires,w,h)
            v195.previews.forEach{(label,parts)->
                val k=key(label)
                if(k in accepted)return@forEach
                val proposed=geometry(parts,w,h)
                val check=ClueRegionValidation.validateGeometryNormalized(
                    proposed,w,h,gridPoints)
                if(check.usable){
                    newPreviews[k]=proposed
                    newPreviewReasons[k]=v195.diagnostics[label].orEmpty()
                }else{
                    newPreviewReasons[k]="V195_GEOMETRY_REJECTED:"+
                        check.reason+"; original preview preserved; NO canonical write"
                }
            }
            v195.diagnostics.forEach{(label,why)->
                val k=key(label)
                if(k !in accepted && label !in v195.previews)
                    newPreviewReasons[k]=why
            }
        }
'''
s=s.replace(needle,block+needle,1)
src.write_text(s,encoding='utf-8')
(base/'OcrIndependentBoundaryV195.kt').write_text(
    Path(__file__).with_name('higi-v195-boundary.kt.txt').read_text(encoding='utf-8'),
    encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrIndependentBoundaryV195Test.kt'
test.write_text(
    Path(__file__).with_name('higi-v195-boundary-test.kt.txt').read_text(encoding='utf-8'),
    encoding='utf-8')
gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for old,new in (('versionCode = 344','versionCode = 345'),
                ('versionName = "0.15.194"','versionName = "0.15.195"')):
    if t.count(old)!=1:
        raise SystemExit('V195 fail closed: unexpected version baseline '+old)
    t=t.replace(old,new,1)
gradle.write_text(t,encoding='utf-8')
print('Prepared Higi 0.15.195 DRY boundary diagnostic, no new OCR service.')
