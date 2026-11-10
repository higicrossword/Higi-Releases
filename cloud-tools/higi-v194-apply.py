#!/usr/bin/env python3
"""V194 DRY: add flexible semicolon/parenthesis scoring in narrow-column preview."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
base=root/'app/src/main/java/com/example/hebrewcrossword'
engine=base/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
if s.count(needle)!=1:
    raise SystemExit('Missing exact final-review boundary')
block=r'''        // V194: final DRY-only semicolon-weighted review of legacy
        // multi-piece narrow RTL column previews. OCR may merge ";(5)"
        // into "(65)"; do not insist that the digits match grid length.
        // Physical printed-number anchors and source geometry still control
        // whether a candidate can be displayed. Never write canonical.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val v194Before=newPreviews.map{(candidate,g)->
                wire(candidate) to g.lines.map{p->
                    CropRect((p.left*w).roundToInt(),(p.top*h).roundToInt(),
                        (p.right*w).roundToInt(),(p.bottom*h).roundToInt())
                }
            }.toMap()
            val v194=OcrSemicolonBoundaryV194.inspect(
                v194Before,auditWords,expectedWires,w,h)
            v194.previews.forEach{(label,parts)->
                val k=key(label)
                if(k in accepted)return@forEach
                val proposal=geometry(parts,w,h)
                val check=ClueRegionValidation.validateGeometryNormalized(
                    proposal,w,h,gridPoints)
                if(check.usable){
                    newPreviews[k]=proposal
                    newPreviewReasons[k]=v194.diagnostics[label].orEmpty()
                }else{
                    newPreviewReasons[k]="V194_GEOMETRY_REJECTED:"+
                        check.reason+"; manual review; NO canonical write"
                }
            }
            v194.diagnostics.forEach{(label,why)->
                val k=key(label)
                if(k !in accepted && label !in v194.previews)
                    newPreviewReasons[k]=why
            }
        }
'''
s=s.replace(needle,block+needle,1)
engine.write_text(s,encoding='utf-8')
(base/'OcrSemicolonBoundaryV194.kt').write_text(
    Path(__file__).with_name('higi-v194-semicolon.kt.txt').read_text(encoding='utf-8'),
    encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrSemicolonBoundaryV194Test.kt'
test.write_text(
    Path(__file__).with_name('higi-v194-semicolon-test.kt.txt').read_text(encoding='utf-8'),
    encoding='utf-8')
gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for old,new in (('versionCode = 343','versionCode = 344'),
                ('versionName = "0.15.193"','versionName = "0.15.194"')):
    if t.count(old)!=1:
        raise SystemExit('Version invariant failed: '+old)
    t=t.replace(old,new,1)
gradle.write_text(t,encoding='utf-8')
print("Prepared Higi v194 flexible semicolon DRY preview.")
