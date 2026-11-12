#!/usr/bin/env python3
"""Only administrator DRY YEDIOTH_DEKEL_WEEKLY: inspect *final* visible geometry.

Fail closed if the pinned 0.15.200 source differs from the audited revision.
No changes to generic geometry validation, other puzzle series, Firebase or Canonical.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
assets=Path(__file__).resolve().parent
app=root/'app/src/main/java/com/example/hebrewcrossword'
tests=root/'app/src/test/java/com/example/hebrewcrossword'

def once(s, old, new, label):
    count=s.count(old)
    assert count==1, f'{label}: expected once, got {count}'
    return s.replace(old,new,1)

for source,dest in [
  ('OcrWeeklyFinalGeometryV201.kt',app/'OcrWeeklyFinalGeometryV201.kt'),
  ('OcrWeeklyFinalGeometryV201Test.kt',tests/'OcrWeeklyFinalGeometryV201Test.kt')]:
    assert not dest.exists(),f'already present: {dest}'
    data=(assets/source).read_bytes()
    assert len(data)>1000
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    print('CREATE',dest.relative_to(root))

# 1: Source-anchored previews use ACTUAL measured grid edge, not a guessed 0.675
# fixed format column boundary. This change is isolated to Monday/Wednesday
# source-anchored admin DRY proposals; no impact on TARTEY/HAFUCH.
path=app/'HigiLocalOcrCropEngine.kt'
s=path.read_text()
old='''            independent.previews.forEach{(label,pieces)->
                val k=key(label)
                val proposed=geometry(pieces,w,h)
                val valid=ClueRegionValidation.validateGeometryNormalized(
                    proposed,w,h,gridPoints)
'''
new='''            independent.previews.forEach{(label,pieces)->
                val k=key(label)
                // A printed Across word must never pull the proposal into the
                // grid. Use measured source grid points only, never a hardcoded
                // grid position or a similarly numbered clue's old rectangle.
                val gridLeftPx=gridPoints.takeIf{it.size==4}?.minOf{it.x}?.roundToInt()
                val constrained=OcrWeeklyFinalGeometryV201.clipFreshAcross(
                    label,pieces,gridLeftPx,w)
                if(constrained==null){
                    newPreviewReasons[k]="V201_FRESH_GRID_BOUNDARY_UNSAFE: " +
                        "source word starts inside grid; previous preview retained; DRY only"
                    return@forEach
                }
                val proposed=geometry(constrained,w,h)
                val valid=ClueRegionValidation.validateGeometryNormalized(
                    proposed,w,h,gridPoints)
'''
s=once(s,old,new,'Source-based clipped preview')
# Restrict the replacements to the independent source block, before V200 pass.
a=s.index('            independent.previews.forEach{(label,pieces)->')
b=s.index('            independent.reasons.forEach{(label,diagnostic)->',a)
block=s[a:b]
assert 'val legacyCount=' in block and 'OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview' in block
block=once(block,'legacyCount in 2..3 && pieces.size==1',
    'legacyCount in 2..3 && constrained.size==1','complete-line regression guard')
block=once(block,'                        label,pieces,auditWords,valid.reason)',
    '                        label,constrained,auditWords,valid.reason)','narrow-number validation geometry')
block=once(block,'parts=${pieces.size}', 'parts=${constrained.size}','debug piece count')
# Leave clipping annotated as review, never autoaccepted for Canonical.
block=once(block,
    'newPreviewReasons[k]=independent.reasons[label].orEmpty() +',
    'newPreviewReasons[k]=independent.reasons[label].orEmpty() +\n                        (if(constrained!=pieces) " | V201_GRID_CLIPPED_DRy_REVIEW_ONLY" else "") +',
    'clipped review-only status')
s=s[:a]+block+s[b:]

# 2: REMOVE the premature V200 overlap warning computation entirely. The
# intermediate `acceptedPixels()` can later fail actual publishing validation;
# it must not pose as FINAL_TRUSTED when it overlaps a good final candidate.
start='''            // V200 global, NON-DESTRUCTIVE diagnostic pass.'''
end='''        }
        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
i=s.index(start)
j=s.index(end,i)
removed=s[i:j]
assert 'acceptedPixels().forEach' in removed
assert 'OcrWeeklyOverlapReviewV200.assess' in removed
assert 'newPreviewReasons[k]' in removed
s=s[:i]+'''            // V201: cross-clue and self-overlap warnings are deliberately
            // deferred until LocalOcrCropPass has completed its final
            // validateGeometryNormalized/canPublish filtering.  Intermediate
            // `acceptedPixels()` are NOT accepted for final ownership claims.
'''+s[j:]
assert 'OcrWeeklyOverlapReviewV200.assess' not in s
path.write_text(s)
print('MODIFY',path.relative_to(root),'measured grid clipping + final-only conflict pass')

# 3: Final review at the ONLY point where actual verified/previews are known.
path=app/'LocalOcrCropPass.kt'
s=path.read_text()
start='''        return Result(verified,detected?.review.orEmpty(),detected?.wrapped.orEmpty(),'''
final='''        val finalReview=linkedMapOf<ClueEditorModel.Key,String>()
        finalReview.putAll(detected?.review.orEmpty())
        if(BuildConfig.HIGI_DRY_BUILD && refineSharedRows &&
            layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id && detected!=null){
            fun label(k:ClueEditorModel.Key):String =
                (if(k.direction==Direction.HORIZONTAL)"H" else "V")+k.number
            fun pix(g:ClueGeometry):List<CropRect> = g.lines.map{r->
                CropRect((r.left*source.width).roundToInt(),
                    (r.top*source.height).roundToInt(),
                    (r.right*source.width).roundToInt(),
                    (r.bottom*source.height).roundToInt())
            }
            val visible=linkedMapOf<String,OcrWeeklyFinalGeometryV201.Candidate>()
            verified.forEach{(k,g)->visible[label(k)]=OcrWeeklyFinalGeometryV201.Candidate(
                pix(g),OcrWeeklyFinalGeometryV201.Origin.VERIFIED_FINAL)}
            previews.forEach{(k,g)->if(k !in verified){
                val prior=previewWhy[k].orEmpty()
                val origin=when{
                    prior.contains("GEOMETRY_REJECTED") ||
                        prior.contains("LEGACY_PREVIEW") ||
                        prior.contains("V168_") ->
                        OcrWeeklyFinalGeometryV201.Origin.REJECTED_LEGACY_REVIEW
                    prior.contains("SOURCE_ANCHORED_REVIEW_ONLY") ->
                        OcrWeeklyFinalGeometryV201.Origin.SOURCE_ANCHORED_REVIEW
                    else -> OcrWeeklyFinalGeometryV201.Origin.OTHER_REVIEW
                }
                visible[label(k)]=OcrWeeklyFinalGeometryV201.Candidate(pix(g),origin)
            }}
            val measuredGridLeft=gridPoints.takeIf{it.size==4}?.minOf{it.x}?.roundToInt()
            val audit=OcrWeeklyFinalGeometryV201.inspect(visible,
                detected.geometryWords,source.width,measuredGridLeft)
            // A final candidate with its OWN repeated words or actual source
            // grid intrusion cannot count as trusted. Retain as visible DRY
            // preview, without making an automatic/Canonical claim.
            verified.keys.toList().forEach{k->
                if(label(k) in audit.demoteVerified){
                    val g=verified.remove(k) ?: return@forEach
                    previews.putIfAbsent(k,g)
                    DebugLog.w("LOCAL_OCR_V201", "demotedFinal=${label(k)} retainedForManualReview")
                }
            }
            audit.reasons.forEach{(wire,notes)->
                val k=ClueEditorModel.Key(wire.drop(1).toInt(),
                    if(wire.startsWith("H"))Direction.HORIZONTAL else Direction.VERTICAL)
                val detail=notes.joinToString(" | ")
                finalReview[k]=listOf(finalReview[k].orEmpty(),detail)
                    .filter{it.isNotBlank()}.joinToString(" | ")
                previewWhy[k]=listOf(previewWhy[k].orEmpty(),detail)
                    .filter{it.isNotBlank()}.joinToString(" | ")
            }
        }
        return Result(verified,finalReview,detected?.wrapped.orEmpty(),'''
s=once(s,start,final,'Final publishable/previews and grid audit')
assert 'OcrWeeklyFinalGeometryV201.inspect' in s
path.write_text(s)
print('MODIFY',path.relative_to(root),'trust-final cross/self/grid audit and demotion')

# 4: Admin UI consumes final warnings only. The old V200 UI imported early
# previewReasons and could override correct final evidence (the exact bug in
# 4 November H9 / H11). Retain warning visibility and block unresolved edits.
path=app/'AdminOcrRecropActivity.kt'
s=path.read_text()
# Replace V200's stale reasons import. V201's finalResult.review has the truth.
old='''                // Retain warnings for accepted AND preview-only candidates.
                // Do not discard a warning merely because `trusted` won UI order.
                if(BuildConfig.HIGI_DRY_BUILD &&
                    layoutProfile.id==OcrSeriesProfilesV197.WEEKLY.id){
                    result?.previewReasons.orEmpty().forEach{(key,why)->
                        if(why.contains("V200_CROSS_CLUE_OVERLAP_REVIEW_ONLY"))
                            reasons[key]=why
                    }
                }
'''
s=once(s,old,'                // V201: result.review is post-validation; never re-import the\n                // early V200 provisional overlap warning from previewReasons.\n','Remove stale warning import')
# All existing V200 checks now use only V201's final BLOCK warnings.
assert s.count('hasV200WeeklyOverlapWarning')>=5
s=s.replace('hasV200WeeklyOverlapWarning','hasV201FinalGeometryBlock')
s=once(s,
  '''reasons[key]?.contains("V200_CROSS_CLUE_OVERLAP_REVIEW_ONLY")==true''',
  '''reasons[key]?.contains("V201_FINAL_GEOMETRY_BLOCK")==true''',
  'Final-only approval gate')
s=once(s,
  '''(if(hasV201FinalGeometryBlock(k)) " · חפיפה לבדיקה" else "")''',
  '''(if(reasons[k]?.contains("V201_FINAL_GEOMETRY_")==true) " · גבולות לבדיקה" else "")''',
  'Show all V201 final findings in clue dropdown')
s=once(s,
  '''            if(candidateMode && hasV201FinalGeometryBlock(key))''',
  '''            if(candidateMode && reasons[key]?.contains("V201_FINAL_GEOMETRY_")==true)''',
  'Expose nonblocking legacy warnings in the details text')
s=once(s,
  '''                append("\\nהתנגשות חיתוכים לבדיקה ידנית — לא ניתן לסמן לאישור: ")''',
  '''                append("\\nבדיקת גבולות החיתוך לאחר אימות סופי: ")''',
  'Accurate diagnostic wording')
s=once(s,
  '''            toast("חפיפת OCR לא נפתרה; אין אפשרות לסמן לאישור")''',
  '''            toast("גבולות החיתוך דורשים תיקון ידני לפני אישור")''',
  'Blocking conflict toast')
path.write_text(s)
print('MODIFY',path.relative_to(root),'final-only UI diagnostic and safe approval gate')

# 5: Local version only. Pipeline calls existing sync-release-version.py.
path=root/'app/build.gradle.kts'
s=path.read_text()
s=once(s,'versionCode = 350','versionCode = 351','v201 code')
s=once(s,'versionName = "0.15.200"','versionName = "0.15.201"','v201 name')
path.write_text(s)
print('V201_DRY_SOURCE_PATCH_COMPLETE')