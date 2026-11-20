#!/usr/bin/env python3
"""Staged v212 -> v213 series-only OCR read/preview activation; no release or Canonical writes."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
base=root/"app/src/main/java/com/example/hebrewcrossword"
main=base/"MainActivity.kt"
source=main.read_text()
old="        val local=LocalOcrCropPass.run(this,original,prepared.crossword,prepared.points,stage)"
new="""        // Explicit stable series identity only: do not select OCR geometry rules by appearance.
        val ocrSeriesId=OcrSeriesActivationV213.forCatalogId(
            CrosswordCatalog.fromCanonicalTitle(prepared.title)?.id)
        val local=LocalOcrCropPass.run(this,original,prepared.crossword,prepared.points,stage,
            refineSharedRows=ocrSeriesId!=null,layoutSeriesId=ocrSeriesId)"""
assert source.count(old)==1,("main auto import locator",source.count(old))
main.write_text(source.replace(old,new))
runner=base/"AdminLibraryRedecodeRunner.kt"
source=runner.read_text()
old="            val localCrop=LocalOcrCropPass.run(context,bitmap,cw,grid,stage)"
new="""            val cropSeriesId=OcrSeriesActivationV213.forCatalogId(
                CrosswordCatalog.fromCanonicalTitle(original.title)?.id)
            val localCrop=LocalOcrCropPass.run(context,bitmap,cw,grid,stage,
                refineSharedRows=cropSeriesId!=null,layoutSeriesId=cropSeriesId)"""
assert source.count(old)==1,("runner",source.count(old))
runner.write_text(source.replace(old,new))
policy=base/"OcrSeriesActivationV213.kt"
assert not policy.exists(),str(policy)
policy.write_text("""package com.example.hebrewcrossword

/**
 * Opts the three already tested series into their existing source-word OCR review
 * engine. NEVER promotes review-only crops into trusted/canonical automatically.
 * Unknown and ambiguous series fail closed. No change to series' frozen OCR rules.
 */
object OcrSeriesActivationV213 {
    fun forCatalogId(id:String?):String? = when(id) {
        "YEDIOTH_DEKEL_WEEKLY", "YEDIOTH_MONDAY_DEKEL", "YEDIOTH_WEDNESDAY_DEKEL" ->
            OcrSeriesProfilesV197.WEEKLY.id
        "HAFUCH_DEKEL" -> OcrSeriesProfilesV197.HAFUCH.id
        else -> null
    }
}
""")
test=root/"app/src/test/java/com/example/hebrewcrossword/OcrSeriesActivationV213Test.kt"
assert not test.exists()
test.write_text("""package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class OcrSeriesActivationV213Test {
    @Test fun selectedSeriesHaveExactProfiles() {
        assertEquals("YEDIOTH_DEKEL_WEEKLY", OcrSeriesActivationV213.forCatalogId("YEDIOTH_MONDAY_DEKEL"))
        assertEquals("YEDIOTH_DEKEL_WEEKLY", OcrSeriesActivationV213.forCatalogId("YEDIOTH_WEDNESDAY_DEKEL"))
        assertEquals("YEDIOTH_DEKEL_WEEKLY", OcrSeriesActivationV213.forCatalogId("YEDIOTH_DEKEL_WEEKLY"))
        assertEquals("HAFUCH_DEKEL", OcrSeriesActivationV213.forCatalogId("HAFUCH_DEKEL"))
    }
    @Test fun noOtherSeriesActivate() {
        for(id in listOf<String?>(null, "", "TARTEY_DEKEL", "MAARIV_ODED_ROZEN", "YEDIOTH", "HAFUCH", "OTHER"))
            assertNull(OcrSeriesActivationV213.forCatalogId(id))
    }
}
""")
print("STAGED 4 Kotlin files",main,runner,policy,test)

# Promote ONLY exact-number, bounded, non-inferred V199 weekly proposals.
crop=base/"LocalOcrCropPass.kt"
source=crop.read_text()
anchor="""        return Result(verified,finalReview,detected?.wrapped.orEmpty(),"""
assert source.count(anchor)==1,("return anchor",source.count(anchor))
insert="""        // Exact-series V213 promotion. A review rectangle is not automatically trusted:
        // require both printed numbers, a fully measured source, non-inferred start,
        // no other clue collision, and existing geometry evidence validation.
        if(layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id && refineSharedRows &&
            detected!=null && detected.geometryWords.isNotEmpty()) {
            val words=detected.geometryWords
            fun wire(k:ClueEditorModel.Key)=
                (if(k.direction==Direction.HORIZONTAL)"H" else "V")+k.number
            fun pixels(g:ClueGeometry):List<CropRect> = g.lines.map { part ->
                CropRect((part.left*source.width).roundToInt(),(part.top*source.height).roundToInt(),
                    (part.right*source.width).roundToInt(),(part.bottom*source.height).roundToInt())
            }
            val all=(verified+previews).mapKeys{wire(it.key)}.mapValues{pixels(it.value)}
            val clashes=OcrWeeklySourceAnchorsV199.conflictingKeys(all,words)
            previews.toMap().forEach { (key,proposal) ->
                if(key in verified || key in detected.geometryNeedsReview ||
                    key in detected.sharedRowNeedsReview ||
                    !OcrSeriesPromotionV213.onlyNoOldCrop(finalReview[key]) ||
                    !OcrSeriesPromotionV213.onlyNoOldCrop(detected.review[key])) return@forEach
                val reason=previewWhy[key].orEmpty()
                val label=wire(key)
                val strong=OcrSeriesPromotionV213.mayTrustWeeklyV199(
                    layoutSeriesId, reason,
                    ownStart=OcrWeeklySourceAnchorsV199.ownsPrintedNumber(label,pixels(proposal),words),
                    hasConflict=label in clashes,
                    sourceWidth=source.width,sourceHeight=source.height
                )
                if(!strong)return@forEach
                val supported=proposal.copy(evidence=ClueGeometryEvidence.LOCAL_OCR_ANCHORED)
                val valid=ClueRegionValidation.validateGeometryNormalized(
                    supported,source.width,source.height,gridPoints).usable
                if(valid && ClueGeometryEvidencePolicy.canPublish(supported)) {
                    verified[key]=supported
                    previews.remove(key)
                    previewWhy.remove(key)
                    DebugLog.i("LOCAL_OCR_V213","key=$label series=YEDIOTH_DEKEL_WEEKLY " +
                        "status=EXACT_ANCHOR_LOCAL_TRUSTED noOverwrite=true")
                }
            }
        }
"""
source=source.replace(anchor,insert+anchor)
crop.write_text(source)
policy=base/"OcrSeriesPromotionV213.kt"
assert not policy.exists()
policy.write_text("""package com.example.hebrewcrossword

/**
 * Only promote independently numbered weekly source crops. This does NOT remove
 * review/geometry safeguards or supersede saved manual/canonical coordinates.
 */
object OcrSeriesPromotionV213 {
    // NO_SAFE_OCR_CROP describes the absent previous geometry, not the independently
    // located V199 candidate. Every other review status stays blocking.
    fun onlyNoOldCrop(note:String?):Boolean = note.isNullOrBlank() || note.trim()=="NO_SAFE_OCR_CROP"

    fun mayTrustWeeklyV199(
        seriesId:String?,diagnostic:String,ownStart:Boolean,hasConflict:Boolean,
        sourceWidth:Int,sourceHeight:Int
    ):Boolean =
        seriesId==OcrSeriesProfilesV197.WEEKLY.id &&
        diagnostic.startsWith("V199_SOURCE_ANCHORED_REVIEW_ONLY:") &&
        diagnostic.contains("inferred=false") &&
        !diagnostic.contains("next=END_OF_COLUMN") &&
        !diagnostic.contains("V200_") &&
        !diagnostic.contains("V201_") &&
        !diagnostic.contains("V208_") &&
        ownStart && !hasConflict && sourceWidth>=600 && sourceHeight>=350
}
""")
tests=root/"app/src/test/java/com/example/hebrewcrossword/OcrSeriesPromotionV213Test.kt"
assert not tests.exists()
tests.write_text("""package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class OcrSeriesPromotionV213Test {
    private val clear="V199_SOURCE_ANCHORED_REVIEW_ONLY: independent start=5, next=7, inferred=false, pieces=2; no Canonical write"
    private fun check(diag:String=clear,series:String?="YEDIOTH_DEKEL_WEEKLY",
        own:Boolean=true,conflict:Boolean=false,w:Int=1426,h:Int=1103)=
        OcrSeriesPromotionV213.mayTrustWeeklyV199(series,diag,own,conflict,w,h)
    @Test fun onlyStrongPrintedBoundaries() {
        assertTrue(check())
        assertFalse(check(diag=clear.replace("inferred=false","inferred=true")))
        assertFalse(check(diag=clear.replace("next=7","next=END_OF_COLUMN")))
        assertFalse(check(own=false))
        assertFalse(check(conflict=true))
        assertFalse(check(diag=clear+" V201_FINAL_GEOMETRY_BLOCK"))
        assertFalse(check(diag=clear+" V208_INVALID_REPAIR"))
    }
    @Test fun oldMissingGeometryDoesNotVetoIndependentCandidate() {
        assertTrue(OcrSeriesPromotionV213.onlyNoOldCrop(null))
        assertTrue(OcrSeriesPromotionV213.onlyNoOldCrop("NO_SAFE_OCR_CROP"))
        assertFalse(OcrSeriesPromotionV213.onlyNoOldCrop("V201_FINAL_GEOMETRY_BLOCK"))
        assertFalse(OcrSeriesPromotionV213.onlyNoOldCrop("LOCAL_OCR_REVIEW:AMBIGUOUS_START"))
        assertFalse(OcrSeriesPromotionV213.onlyNoOldCrop("NO_SAFE_OCR_CROP | V201_FINAL_GEOMETRY_REVIEW_ONLY"))
    }
    @Test fun weeklyOnly() {
        assertFalse(check(series="HAFUCH_DEKEL"))
        assertFalse(check(series="TARTEY_DEKEL"))
        assertFalse(check(series=null))
        assertFalse(check(w=500))
    }
}
""")
print("PROMOTION_FILES",crop.name,policy.name,tests.name)

# Preserve source-matched Canonical/previously verified geometry over new automatic
# OCR proposals. In particular, a stronger OCR suggestion is not user consent to
# retire an existing manual or canonical region.
main=base/"MainActivity.kt"
source=main.read_text()
old="""            putAll(oldTrusted)
            putAll(current)"""
new="""            putAll(current)
            // Source-matched canonical/manual coordinates have precedence.
            putAll(oldTrusted)"""
assert source.count(old)==1,("source matched canonical precedence",source.count(old))
main.write_text(source.replace(old,new))
print("SAFETY_GUARDS: no-old-crop candidate eligible; canonical/manual geometry preserved")
