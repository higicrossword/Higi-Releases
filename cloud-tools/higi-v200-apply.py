#!/usr/bin/env python3
"""DRY ONLY: fix V199 destructive cross-clue arbitration and improve review safety.

Apply against reconstructed, pinned Higi 0.15.199 source. No Firebase/Canonical
changes or deployment. Every textual surgery has fail-closed exact assertions.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
assets=Path(__file__).resolve().parent
app=root/'app/src/main/java/com/example/hebrewcrossword'
tests=root/'app/src/test/java/com/example/hebrewcrossword'

def replace_once(text,old,new,label):
    count=text.count(old)
    assert count==1, f'{label}: expected one replacement, found {count}'
    return text.replace(old,new,1)

for name,dest in [
    ('OcrWeeklyOverlapReviewV200.kt',app/'OcrWeeklyOverlapReviewV200.kt'),
    ('OcrWeeklyOverlapReviewV200Test.kt',tests/'OcrWeeklyOverlapReviewV200Test.kt')]:
    assert not dest.exists(),f'Unexpected existing file {dest}'
    assert (assets/name).exists(),f'Missing source {name}'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes((assets/name).read_bytes())
    print('CREATE',dest.relative_to(root))

engine=app/'HigiLocalOcrCropEngine.kt'
s=engine.read_text()
start_marker='''        // V199 - Yedioth Dekel WEEKLY ONLY.'''
end_marker='''        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}'''
a=s.index(start_marker)
b=s.index(end_marker,a)
block=s[a:b]
assert 'OcrWeeklySourceAnchorsV199.inspect(auditWords,expectedWires,w,h)' in block
assert 'val conflicts=OcrWeeklySourceAnchorsV199.conflictingKeys(allPixels,auditWords)' in block
assert 'removed.forEach{label->' in block
assert 'V199_CROSS_CLUE_OVERLAP' in block
assert block.endswith('        }\n'), 'Unexpected V199 block termination'
# Preserve source OCR recovery exactly, but ensure the new pass never runs
# outside the admin DRY channel.
kept=block[:block.index('            // Compare all same-direction clues, not just segments within each')]
kept=replace_once(kept,
    '''if(refineSharedRows && layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&''',
    '''if(BuildConfig.HIGI_DRY_BUILD && refineSharedRows &&
            layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&''',
    'V200 DRY execution gate')
kept=replace_once(kept,
    '''                val legacyCount=newPreviews[k]?.lines?.size ?: 0
                val shortRegression=legacyCount in 2..3 && pieces.size==1
                if(valid.usable && !shortRegression){
                    newPreviews[k]=proposed
                    newPreviewReasons[k]=independent.reasons[label].orEmpty()''',
    '''                val legacyCount=newPreviews[k]?.lines?.size ?: 0
                val shortRegression=legacyCount in 2..3 && pieces.size==1
                // Never relax global geometry validation.  One printed-number-
                // only 9..23px source crop can still be SHOWN in an admin DRY
                // multi-piece review after independent number-box corroboration.
                val narrowReview= !valid.usable &&
                    OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview(
                        label,pieces,auditWords,valid.reason)
                if((valid.usable || narrowReview) && !shortRegression){
                    newPreviews[k]=proposed
                    newPreviewReasons[k]=independent.reasons[label].orEmpty() +
                        (if(narrowReview) " | V200_NARROW_PRINTED_NUMBER_REVIEW_ONLY: " +
                            "not geometrically approved; no canonical write" else "")''',
    'V200 narrowly constrained preview')
assert 'independent.reasons.forEach' in kept
# No selection/winner/loser and no fallback suppression; the only outcome is
# diagnostic evidence.  Legacy bboxes are explicitly labeled as such.
review='''            // V200 global, NON-DESTRUCTIVE diagnostic pass.  Compare legacy,
            // fresh and accepted proposals, but NEVER delete a proposed crop
            // just because an old broad rectangle overlaps it.  The reviewer
            // needs to see BOTH candidates to decide where words belong.
            fun asPixels(g:ClueGeometry)=g.lines.map{box->CropRect(
                (box.left*w).roundToInt(),(box.top*h).roundToInt(),
                (box.right*w).roundToInt(),(box.bottom*h).roundToInt())}
            val allCandidates=linkedMapOf<String,OcrWeeklyOverlapReviewV200.Candidate>()
            acceptedPixels().forEach{(label,parts)->
                allCandidates[label]=OcrWeeklyOverlapReviewV200.Candidate(parts,
                    OcrWeeklyOverlapReviewV200.Origin.ACCEPTED)
            }
            newPreviews.forEach{(k,g)->
                val label=wire(k)
                allCandidates[label]=OcrWeeklyOverlapReviewV200.Candidate(
                    asPixels(g),if(label in freshKeys)
                        OcrWeeklyOverlapReviewV200.Origin.SOURCE_ANCHORED else
                        OcrWeeklyOverlapReviewV200.Origin.LEGACY_PREVIEW)
            }
            val warnings=OcrWeeklyOverlapReviewV200.assess(allCandidates,auditWords).warnings
            warnings.forEach{(label,conflicts)->
                val k=key(label)
                val prior=newPreviewReasons[k].orEmpty()
                val warning="V200_CROSS_CLUE_OVERLAP_REVIEW_ONLY: " +
                    OcrWeeklyOverlapReviewV200.detail(conflicts) +
                    "; no automatic approval; proposals retained; no canonical write"
                newPreviewReasons[k]=if(prior.isBlank())warning else "$prior | $warning"
                DebugLog.w("LOCAL_OCR_V200","key=$label overlap-review-only="+
                    conflicts.map{it.peer}.sorted().joinToString(","))
            }
            // There is intentionally NO removal from newPreviews, accepted,
            // or unresolved. The administrator UI displays warnings, disables
            // approval and keeps all conflicting DRY review images visible.
        }
'''
s=s[:a]+kept+review+s[b:]
assert 'removed.forEach' not in s[a:s.index(end_marker,a)]
assert 'V199_CROSS_CLUE_OVERLAP' not in s[a:s.index(end_marker,a)]
engine.write_text(s)
print('MODIFY',engine.relative_to(root))

# Restore V178 legacy fallback: V199 had blocked it after removing a crop.
# V200 does not remove proposals and must never hide fallback geometry.
path=app/'LocalOcrCropPass.kt'
s=path.read_text()
old='''                    detected?.review?.get(key)?.contains("V199_CROSS_CLUE_OVERLAP")!=true &&
'''
assert old in s
s=replace_once(s,old,'','Restore non-destructive fallback')
# A number-only narrow geometry is strictly review-only, never verified or
# auto-published. Keep full validation for all other cases, including grid.
start='''            detected?.previewOnly.orEmpty().forEach{(key,geometry)->
                if(key in expected && key !in verified &&
                    ClueRegionValidation.validateGeometryNormalized(
                        geometry,source.width,source.height,gridPoints).usable){
                    previews[key]=geometry
                    previewWhy[key]=detected?.previewDiagnostics?.get(key).orEmpty()
                }
            }
'''
replacement='''            detected?.previewOnly.orEmpty().forEach{(key,geometry)->
                val verdict=ClueRegionValidation.validateGeometryNormalized(
                    geometry,source.width,source.height,gridPoints)
                // Do not change the general minimum box width (24px). DRY only:
                // display one independently anchored NUMBER-ONLY narrow segment
                // of a multiline crop. It is not trusted or approvable as-is.
                val narrowReview=!verdict.usable && BuildConfig.HIGI_DRY_BUILD &&
                    layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&
                    detected?.previewDiagnostics?.get(key)?.contains(
                        "V200_NARROW_PRINTED_NUMBER_REVIEW_ONLY")==true &&
                    OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview(
                        "${if(key.direction==Direction.HORIZONTAL)"H" else "V"}${key.number}",
                        geometry.lines.map{box->CropRect(
                            (box.left*source.width).roundToInt(),
                            (box.top*source.height).roundToInt(),
                            (box.right*source.width).roundToInt(),
                            (box.bottom*source.height).roundToInt())},
                        detected?.geometryWords.orEmpty(),verdict.reason)
                if(key in expected && key !in verified && (verdict.usable || narrowReview)){
                    previews[key]=geometry
                    previewWhy[key]=detected?.previewDiagnostics?.get(key).orEmpty()
                }
            }
'''
s=replace_once(s,start,replacement,'DRY review exception for one narrow number')
s=replace_once(s,'import android.os.SystemClock\n',
               'import android.os.SystemClock\nimport kotlin.math.roundToInt\n',
               'LocalOcrCropPass math import')
# Even a geometrically accepted candidate may overlap an OLD legacy box.
# The diagnostic must reach the admin screen WITHOUT demoting the trusted
# candidate or suppressing any unrelated series.
s=replace_once(s,
    'if(key in expected && key !in verified && key !in previewWhy && why.isNotBlank())',
    'if(key in expected && key !in previewWhy && why.isNotBlank() &&\n                    (key !in verified || (BuildConfig.HIGI_DRY_BUILD &&\n                        layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&\n                        why.contains("V200_CROSS_CLUE_OVERLAP_REVIEW_ONLY"))))',
    'Propagate V200 warning for accepted proposals into review UI')

path.write_text(s)
print('MODIFY',path.relative_to(root))

# Surface the overlap diagnostic even if a usable candidate is already on
# screen; V178 previously showed `reasons` only for empty candidates.
path=app/'AdminOcrRecropActivity.kt'
s=path.read_text()
s=replace_once(s,
    '''                reasons.clear();reasons.putAll(result?.review.orEmpty())''',
    '''                reasons.clear();reasons.putAll(result?.review.orEmpty())
                // Retain warnings for accepted AND preview-only candidates.
                // Do not discard a warning merely because `trusted` won UI order.
                if(BuildConfig.HIGI_DRY_BUILD &&
                    layoutProfile.id==OcrSeriesProfilesV197.WEEKLY.id){
                    result?.previewReasons.orEmpty().forEach{(key,why)->
                        if(why.contains("V200_CROSS_CLUE_OVERLAP_REVIEW_ONLY"))
                            reasons[key]=why
                    }
                }''',
    'V200 import warnings for visible candidates')
s=replace_once(s,
    '''    private fun selectedKey():ClueEditorModel.Key?=keys.getOrNull(spinner.selectedItemPosition)''',
    '''    private fun hasV200WeeklyOverlapWarning(key:ClueEditorModel.Key?):Boolean =
        key!=null && BuildConfig.HIGI_DRY_BUILD &&
            layoutProfile.id==OcrSeriesProfilesV197.WEEKLY.id &&
            reasons[key]?.contains("V200_CROSS_CLUE_OVERLAP_REVIEW_ONLY")==true
    private fun selectedKey():ClueEditorModel.Key?=keys.getOrNull(spinner.selectedItemPosition)''',
    'V200 warning predicate')
s=replace_once(s,
    '''keys.map { k -> keyLabel(k) + when {''',
    '''keys.map { k -> keyLabel(k) +
                (if(hasV200WeeklyOverlapWarning(k)) " · חפיפה לבדיקה" else "") + when {''',
    'V200 spinner warning')
s=replace_once(s,
    '''            if(candidateMode && key !in candidates)append("\\nסיבת אי-זיהוי:''',
    '''            if(candidateMode && hasV200WeeklyOverlapWarning(key))
                append("\\nהתנגשות חיתוכים לבדיקה ידנית — לא ניתן לסמן לאישור: ")
                    .append(reasons[key])
            if(candidateMode && key !in candidates)append("\\nסיבת אי-זיהוי:''',
    'V200 visible warning in details')
s=replace_once(s,
    '''        approveButton.isEnabled=!loading && !saving && selected in candidates &&''',
    '''        approveButton.isEnabled=!loading && !saving && selected in candidates &&
            !hasV200WeeklyOverlapWarning(selected) &&''',
    'V200 prevent approval on conflict')
s=replace_once(s,
    '''    private fun toggleApproval() {
        val key=selectedKey()?:return''',
    '''    private fun toggleApproval() {
        val key=selectedKey()?:return
        if(hasV200WeeklyOverlapWarning(key)){
            toast("חפיפת OCR לא נפתרה; אין אפשרות לסמן לאישור")
            return
        }''',
    'V200 guard approval action')
s=replace_once(s,
    '''        saveButton.isEnabled=ready && approved.isNotEmpty()''',
    '''        saveButton.isEnabled=ready && approved.isNotEmpty() &&
            approved.none{hasV200WeeklyOverlapWarning(it)}''',
    'V200 prevent saving approved overlap')
path.write_text(s)
print('MODIFY',path.relative_to(root))

# Version only; sync-release-version.py will update matching LOCAL version
# metadata without touching Firebase rules/backend or calling deploy.
path=root/'app/build.gradle.kts'
s=path.read_text()
s=replace_once(s,'versionCode = 349','versionCode = 350','version code')
s=replace_once(s,'versionName = "0.15.199"','versionName = "0.15.200"','version name')
path.write_text(s)
print('V200_DRY_SOURCE_INTEGRATED')