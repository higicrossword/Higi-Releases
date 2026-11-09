#!/usr/bin/env python3
"""Higi v191 DRY from pinned v190; reviewer-only source-word diagnostics."""
from pathlib import Path
import sys
root=Path(sys.argv[1]);base=root/'app/src/main/java/com/example/hebrewcrossword'
engine=base/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')
needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
if s.count(needle)!=1:raise SystemExit('Expected v190 completion boundary missing')
block=r'''        // V191: Independent DRY administrator preview audit. Source-word
        // extraction can decline silently if the printed number or length
        // token is absent. Expose diagnostic evidence and WITHHOLD obviously
        // unsafe broad proposals. Never mutate accepted or canonical crops.
        if(refineSharedRows && auditWords.isNotEmpty()){
            val current=newPreviews.map{(candidate,g)->
                wire(candidate) to g.lines.map{piece->
                    CropRect((piece.left*w).roundToInt(),(piece.top*h).roundToInt(),
                        (piece.right*w).roundToInt(),(piece.bottom*h).roundToInt())
                }
            }.toMap()
            val safety=OcrPreviewSafetyAuditV191.inspect(
                current,auditWords,expectedWires,w,h)
            safety.diagnostics.forEach{(label,diagnosis)->
                val k=key(label)
                val earlier=newPreviewReasons[k].orEmpty()
                newPreviewReasons[k]=if(earlier.isEmpty())diagnosis else
                    earlier+" | "+diagnosis
            }
            safety.withheld.forEach{(label,reason)->
                val k=key(label)
                newPreviews.remove(k)
                newPreviewReasons[k]=reason+" | "+safety.diagnostics[label].orEmpty()
                unresolved.putIfAbsent(k,"V191_ADMIN_REVIEW_UNSAFE_PREVIEW")
            }
        }
'''
s=s.replace(needle,block+needle,1)
engine.write_text(s,encoding='utf-8')
(base/'OcrPreviewSafetyAuditV191.kt').write_text(
    Path(__file__).with_name('higi-v191-audit.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrPreviewSafetyAuditV191Test.kt'
test.write_text(Path(__file__).with_name('higi-v191-audit-test.kt.txt').read_text(encoding='utf-8'),encoding='utf-8')
gradle=root/'app/build.gradle.kts'
t=gradle.read_text(encoding='utf-8')
for old,new in (('versionCode = 340','versionCode = 341'),
                ('versionName = "0.15.190"','versionName = "0.15.191"')):
    if t.count(old)!=1:raise SystemExit('Version invariant failed: '+old)
    t=t.replace(old,new,1)
gradle.write_text(t,encoding='utf-8')
print("Prepared Higi v191: OCR source-word safety and diagnostics.")
