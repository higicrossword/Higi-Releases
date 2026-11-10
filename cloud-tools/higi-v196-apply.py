#!/usr/bin/env python3
"""Apply Higi 0.15.196 admin-only OCR review preservation patch to pinned v195."""
from pathlib import Path
import sys

root=Path(sys.argv[1]);base=root/'app/src/main/java/com/example/hebrewcrossword'
engine=base/'HigiLocalOcrCropEngine.kt'
s=engine.read_text(encoding='utf-8')

def replace_one(before,after,scope):
    global s
    if s.count(before)!=1:
        raise SystemExit(f'V196 fail closed: expected one {scope}, found {s.count(before)}')
    s=s.replace(before,after,1)

replace_one('''        val newPreviews=linkedMapOf<ClueEditorModel.Key,ClueGeometry>()''',
'''        // Independent raw V178 evidence for the V196 DRY rescue pass.
        // Never added to trusted, canonical or weekly import paths.
        val v196LegacyV178=linkedMapOf<String,List<CropRect>>()
        val newPreviews=linkedMapOf<ClueEditorModel.Key,ClueGeometry>()''','newPreviews')
replace_one('''            reconstructed.previews.forEach{(label,parts)->
                val k=key(label)''',
'''            reconstructed.previews.forEach{(label,parts)->
                if(parts.size>=4)v196LegacyV178[label]=parts
                val k=key(label)''','V178 previews')

needle='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
block='''        // V196 - independent administrator DRY review bridge. The V193/V195
        // stages used to skip replacing a V178 preview when a key was present
        // in the INTERNAL accepted map, even if the FINAL downstream safety
        // policy excludes that key from verified. Never mutate accepted here.
        // Tighten eligibility to >=4 legacy rows, narrow RTL column, an
        // inline next printed-number text marker AND exact source WORD anchors.
        if(refineSharedRows && auditWords.isNotEmpty() && v196LegacyV178.isNotEmpty()){
            val rescue=OcrLegacyReviewBridgeV196.inspect(
                v196LegacyV178,lines,auditWords,expectedWires,w,h)
            rescue.previews.forEach{(label,parts)->
                val k=key(label)
                // Preserve previously refined 1..3-piece previews.
                if(newPreviews[k]?.lines?.size?.let{it<4}==true)return@forEach
                val proposal=geometry(parts,w,h)
                val verdict=ClueRegionValidation.validateGeometryNormalized(
                    proposal,w,h,gridPoints)
                if(verdict.usable){
                    newPreviews[k]=proposal
                    newPreviewReasons[k]=rescue.diagnostics[label].orEmpty()
                    DebugLog.i("LOCAL_OCR_V196","key=$label parts=${parts.size} "+
                        "status=ADMIN_PREVIEW_ONLY oldAccepted=${k in accepted} noCloudWrite=true")
                }else{
                    newPreviewReasons[k]="V196_GEOMETRY_REJECTED:"+verdict.reason+
                        "; original candidate preserved; NO canonical write"
                }
            }
        }
        // V196: geometric no-conflict does NOT prove a one-row clue complete.
        // OCR line-text evidence can mark the trusted *local review* candidate
        // as unverified, without changing accepted or any persisted geometry.
        val v196Incomplete=if(refineSharedRows && auditWords.isNotEmpty())
            OcrClueCompletenessV196.review(
                acceptedPixels(),lines,auditWords,expectedWires,w,h)
                .mapKeys{key(it.key)} else emptyMap()
        v196Incomplete.forEach{(k,why)->
            val prior=newPreviewReasons[k].orEmpty()
            newPreviewReasons[k]=listOf(prior,why).filter{it.isNotBlank()}
                .joinToString(" | ")
            DebugLog.i("LOCAL_OCR_V196","key=${wire(k)} status=INCOMPLETE_REVIEW_ONLY")
        }
'''
replace_one(needle,block+needle,'review completion boundary')

replace_one('''finalAudit?.needsManualReview.orEmpty().mapKeys{key(it.key)}+anchorReview,''',
'''finalAudit?.needsManualReview.orEmpty().mapKeys{key(it.key)}+
                anchorReview+v196Incomplete,''','manual review map')
replace_one('''finalAudit?.noDetectedConflict.orEmpty().map(::key).toSet(),''',
'''finalAudit?.noDetectedConflict.orEmpty().map(::key).toSet()-v196Incomplete.keys,''',
'no-conflict map')
replace_one('''            }.mapKeys{key(it.key)}+anchorReview.mapValues{(k,reason)->
                "OCR boundary $reason; manual review required before accepting this clue."
            },''',
'''            }.mapKeys{key(it.key)}+anchorReview.mapValues{(k,reason)->
                "OCR boundary $reason; manual review required before accepting this clue."
            }+v196Incomplete,''','diagnostic map')
replace_one('''            } + v168Inferred.associateWith{k->
                if(finalAudit?.states?.get(wire(k))==OcrCandidateBoundaryReviewV165.State.CONFLICT)
                    OcrCandidateBoundaryReviewV165.State.CONFLICT
                else OcrCandidateBoundaryReviewV165.State.UNCERTAIN
            }),''',
'''            } + v168Inferred.associateWith{k->
                if(finalAudit?.states?.get(wire(k))==OcrCandidateBoundaryReviewV165.State.CONFLICT)
                    OcrCandidateBoundaryReviewV165.State.CONFLICT
                else OcrCandidateBoundaryReviewV165.State.UNCERTAIN
            } + v196Incomplete.keys.associateWith{
                OcrCandidateBoundaryReviewV165.State.UNCERTAIN
            }),''','geometry state map')
replace_one('''            applied.map(::key).toSet()+anchorRepaired,auditRows,auditWords,''',
'''            (applied.map(::key).toSet()+anchorRepaired)-v196Incomplete.keys,
            auditRows,auditWords,''','auto repaired map')
engine.write_text(s,encoding='utf-8')

for path,source in [
    ('OcrLegacyReviewBridgeV196.kt','higi-v196-legacy-bridge.kt.txt'),
    ('OcrClueCompletenessV196.kt','higi-v196-completeness.kt.txt')]:
    target=base/path
    if target.exists():raise SystemExit('V196 fail closed: '+path+' already exists')
    target.write_text(Path(__file__).with_name(source).read_text(encoding='utf-8'),encoding='utf-8')
test=root/'app/src/test/java/com/example/hebrewcrossword/OcrReviewSafetyV196Test.kt'
if test.exists():raise SystemExit('V196 test already exists')
test.write_text(Path(__file__).with_name('higi-v196-regression-test.kt.txt')
                .read_text(encoding='utf-8'),encoding='utf-8')
gradle=root/'app/build.gradle.kts';t=gradle.read_text(encoding='utf-8')
for old,new in [('versionCode = 345','versionCode = 346'),
                ('versionName = "0.15.195"','versionName = "0.15.196"')]:
    if t.count(old)!=1:raise SystemExit('Version invariant '+old)
    t=t.replace(old,new,1)
gradle.write_text(t,encoding='utf-8')
print('Applied Higi 0.15.196 DRY: isolated H1 preview, incomplete H5 review, no trusted/canonical mutation')