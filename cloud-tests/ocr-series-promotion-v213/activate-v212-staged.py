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
                    terminalVisible=OcrSeriesPromotionV213.terminalEnumerationInLastRow(pixels(proposal),words),
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
    // For automatic use, a crop needs the actual printed answer-length token.
    // Review candidates lacking this proof instead of silently dropping "(3)".
    private val enumeration=Regex("^\\\\(\\\\d{1,2}(?:[, ]\\\\d{1,2})*\\\\)[.:;,]?$")
    fun terminalEnumerationInLastRow(
        parts:List<CropRect>,words:List<OcrSharedRowSplitterV161.Word>
    ):Boolean {
        val end=parts.lastOrNull()?:return false
        return words.any { word ->
            val b=word.box
            b.valid && word.confidence>=15 &&
                enumeration.matches(word.text.trim()) &&
                b.left>=end.left && b.right<=end.right &&
                b.top>=end.top && b.bottom<=end.bottom
        }
    }

    // NO_SAFE_OCR_CROP describes the absent previous geometry, not the independently
    // located V199 candidate. Every other review status stays blocking.
    fun onlyNoOldCrop(note:String?):Boolean = note.isNullOrBlank() || note.trim()=="NO_SAFE_OCR_CROP"

    fun mayTrustWeeklyV199(
        seriesId:String?,diagnostic:String,ownStart:Boolean,terminalVisible:Boolean,hasConflict:Boolean,
        sourceWidth:Int,sourceHeight:Int
    ):Boolean =
        seriesId==OcrSeriesProfilesV197.WEEKLY.id &&
        diagnostic.startsWith("V199_SOURCE_ANCHORED_REVIEW_ONLY:") &&
        diagnostic.contains("inferred=false") &&
        !diagnostic.contains("next=END_OF_COLUMN") &&
        !diagnostic.contains("V200_") &&
        !diagnostic.contains("V201_") &&
        !diagnostic.contains("V208_") &&
        ownStart && terminalVisible && !hasConflict && sourceWidth>=600 && sourceHeight>=350
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
        own:Boolean=true,terminal:Boolean=true,conflict:Boolean=false,w:Int=1426,h:Int=1103)=
        OcrSeriesPromotionV213.mayTrustWeeklyV199(series,diag,own,terminal,conflict,w,h)
    @Test fun onlyStrongPrintedBoundaries() {
        assertTrue(check())
        assertFalse(check(diag=clear.replace("inferred=false","inferred=true")))
        assertFalse(check(diag=clear.replace("next=7","next=END_OF_COLUMN")))
        assertFalse(check(own=false))
        assertFalse(check(terminal=false))
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
new="""            if(ocrSeriesId==null) {
                // Preserve the unchanged v212 behavior for unrelated series.
                putAll(oldTrusted)
                putAll(current)
            } else {
                putAll(current)
                // Source-matched canonical/manual coordinates have precedence.
                putAll(oldTrusted)
            }"""
assert source.count(old)==1,("source matched canonical precedence",source.count(old))
main.write_text(source.replace(old,new))
print("SAFETY_GUARDS: no-old-crop candidate eligible; canonical/manual geometry preserved")

# Enable the already-frozen V199 source-word candidate producer in ordinary builds
# exclusively when the caller has selected the exact weekly series id. No geometry
# rule, threshold, mask or source-number inference algorithm changes.
engine=base/"HigiLocalOcrCropEngine.kt"
src=engine.read_text()
old="""if(BuildConfig.HIGI_DRY_BUILD && refineSharedRows &&
            layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&
            auditWords.isNotEmpty()) {"""
new="""if(refineSharedRows &&
            layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id &&
            auditWords.isNotEmpty()) {"""
assert src.count(old)==1,("V199 weekly producer guard",src.count(old))
src=src.replace(old,new)
engine.write_text(src)

# The final independent V201 audit must run in normal builds too; otherwise
# the newly promoted boxes would bypass the source-grid and overlap vetoes.
crop=base/"LocalOcrCropPass.kt"
src=crop.read_text()
old="""if(BuildConfig.HIGI_DRY_BUILD && refineSharedRows &&
            layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id && detected!=null){"""
new="""if(refineSharedRows &&
            layoutSeriesId==OcrSeriesProfilesV197.WEEKLY.id && detected!=null){"""
assert src.count(old)==1,("V201 final audit guard",src.count(old))
crop.write_text(src.replace(old,new))
print("PRODUCTION_WEEKLY_V199_ACTIVATION: series-only; DRY V208 repair remains review-only")

# HAFUCH_DEKEL: separate, conservative, source-word based REVIEW ONLY candidate
# proposal path. Reuses the existing OCR word pass, never the Yedioth V199 rules.
hafuch=base/"HafuchOcrWordReviewV214.kt"
assert not hafuch.exists()
hafuch.write_text("""package com.example.hebrewcrossword

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Exactly HAFUCH_DEKEL, not a publisher-wide shared OCR rule.
 * Source-grounded physical word crops for administrator review only.
 * Neither AUTO-TRUSTED nor Canonical/Firebase writes occur here.
 */
internal object HafuchOcrWordReviewV214 {
    data class Result(val proposals:Map<String,List<CropRect>>,
                      val reasons:Map<String,String>)
    private val start=Regex("^[0-9]{1,2}[.:]$")
    private val enumToken=Regex("^\\\\(\\\\d{1,2}(?:[, ]\\\\d{1,2})*\\\\)[.:;,]?$")
    fun allowedSeries(id:String?):Boolean=id=="HAFUCH_DEKEL"
    fun printedNumber(token:String):Int? {
        val s=token.trim()
        return if(start.matches(s))s.dropLast(1).toIntOrNull() else null
    }
    fun printedLength(token:String):Boolean=enumToken.matches(token.trim())
    private fun cx(b:CropRect)=(b.left+b.right)/2
    private fun cy(b:CropRect)=(b.top+b.bottom)/2

    fun inspect(
        seriesId:String?,
        words:List<OcrSharedRowSplitterV161.Word>,
        lines:List<OcrTextLocatorV033.Line>,
        expected:Set<String>,
        gridRightPx:Int?,w:Int,h:Int
    ):Result {
        val rejected=Result(emptyMap(),emptyMap())
        if(!allowedSeries(seriesId) || gridRightPx==null || w<600 || h<350 ||
           gridRightPx !in (w*.35).toInt()..(w*.80).toInt() ||
           expected.count{it.startsWith("H")}!=14 ||
           expected.count{it.startsWith("V")}!=14) return rejected
        val margin=max(3,w/350)
        val minLeft=gridRightPx+margin
        val horizontal=lines.filter{it.box.valid && it.box.left>=minLeft &&
            it.text.trim().startsWith("מאוזן")}
        val vertical=lines.filter{it.box.valid && it.box.left>=minLeft &&
            it.text.trim().startsWith("מאונך")}
        // Missing/duplicate printed headings are not permission to invent sections.
        if(horizontal.size!=1 || vertical.size!=1) return rejected
        val hTop=horizontal.single().box.top
        val vTop=vertical.single().box.top
        if(hTop !in 0 until vTop || vTop !in 0 until h) return rejected

        val src=words.filter{it.box.valid && it.confidence>=15 &&
            it.box.left>=minLeft && it.box.right<w && it.box.top>=hTop &&
            it.box.bottom<=h}
        if(src.isEmpty())return rejected
        val heights=src.map{it.box.bottom-it.box.top}.filter{it>=5}.sorted()
        if(heights.isEmpty())return rejected
        val tolerance=(heights[heights.size/2]/2).coerceIn(5,15)
        val proposals=linkedMapOf<String,List<CropRect>>()
        val reasons=linkedMapOf<String,String>()
        for(dir in listOf('H','V')) {
            val begin=if(dir=='H')hTop else vTop
            val end=if(dir=='H')vTop else h
            val inSection=src.filter{cy(it.box)>=begin && cy(it.box)<end}
            val nums=expected.filter{it.firstOrNull()==dir}
                .mapNotNull{it.drop(1).toIntOrNull()}.sorted()
            val anchors=inSection.filter{it.confidence>=60 &&
                printedNumber(it.text) in nums}
                .groupBy{printedNumber(it.text)}
            // The final clue requires additional independent end-of-section evidence.
            // No unconditional extension into the footer or opposite heading.
            for(index in 0 until nums.lastIndex) {
                val label=dir.toString()+nums[index]
                val own=anchors[nums[index]]?.singleOrNull()
                val next=anchors[nums[index+1]]?.singleOrNull()
                if(own==null || next==null) {
                    reasons[label]="HAFUCH_START_OR_NEXT_UNVERIFIED"
                    continue
                }
                val a=own.box;val b=next.box
                if(cy(a)>cy(b)+tolerance ||
                   (abs(cy(a)-cy(b))<=tolerance && cx(a)<=cx(b))) {
                    reasons[label]="HAFUCH_NON_MONOTONIC_PRINTED_ANCHORS"
                    continue
                }
                val selected=inSection.filter{token->
                    val box=token.box
                    val y=cy(box)
                    val afterStart=y>cy(a)+tolerance ||
                        (abs(y-cy(a))<=tolerance && cx(box)<=cx(a))
                    val beforeNext=y<cy(b)-tolerance ||
                        (abs(y-cy(b))<=tolerance && cx(box)>cx(b))
                    afterStart && beforeNext
                }.distinct().sortedWith(compareBy({cy(it.box)},{-cx(it.box)}))
                if(own !in selected || selected.size<3 ||
                   selected.any{it!==own && printedNumber(it.text)!=null}) {
                    reasons[label]="HAFUCH_SHARED_ROW_OR_OWNERSHIP_AMBIGUOUS"
                    continue
                }
                val rows=mutableListOf<MutableList<OcrSharedRowSplitterV161.Word>>()
                selected.forEach{word->
                    val previous=rows.lastOrNull()
                    if(previous!=null && abs(cy(word.box)-previous.map{cy(it.box)}.average())<=tolerance)
                        previous.add(word)
                    else rows.add(mutableListOf(word))
                }
                if(rows.size !in 1..6)continue
                val rects=rows.map { row ->
                    CropRect((row.minOf{it.box.left}-2).coerceAtLeast(minLeft),
                        (row.minOf{it.box.top}-2).coerceAtLeast(begin),
                        (row.maxOf{it.box.right}+2).coerceAtMost(w),
                        (row.maxOf{it.box.bottom}+2).coerceAtMost(end))
                }
                if(rects.any{!it.valid || it.right-it.left<9})continue
                // Without source OCR recognition of the terminal enumeration,
                // keep a visible candidate, but NEVER make it trusted.
                val lengthRecognized=selected.any{printedLength(it.text)}
                proposals[label]=rects
                reasons[label]=if(lengthRecognized)
                    "HAFUCH_SOURCE_WORD_REVIEW_ONLY: numbered boundaries and length seen"
                    else "HAFUCH_LENGTH_UNVERIFIED_REVIEW_ONLY"
            }
        }
        return Result(proposals,reasons)
    }
}
""")
engine=base/"HigiLocalOcrCropEngine.kt"
src=engine.read_text()
anchor="""        expected.forEach{e->val k=key(e.key); if(k !in accepted)unresolved.putIfAbsent(k,"NO_SAFE_OCR_CROP")}"""
assert src.count(anchor)==1,("HAFUCH insertion point",src.count(anchor))
replacement="""        // Hafuch source-word candidates are independent and strictly review-only.
        // Do not replace a verified candidate or a more-specific existing preview.
        if(refineSharedRows && layoutSeriesId==OcrSeriesProfilesV197.HAFUCH.id &&
            auditWords.isNotEmpty() && crossword.rows==13 && crossword.cols==13 &&
            HafuchGridTemplate.forSeries(layoutSeriesId)?.let{
                GridConsistency.blockedMask(it)==GridConsistency.blockedMask(crossword)
            }==true) {
            val gridRight=gridPoints.takeIf{it.size==4}?.maxOf{it.x}?.roundToInt()
            val hafuch=HafuchOcrWordReviewV214.inspect(layoutSeriesId,auditWords,lines,
                expectedWires,gridRight,w,h)
            hafuch.proposals.forEach { (label,parts) ->
                val k=key(label)
                if(k !in accepted && k !in newPreviews) {
                    val candidate=geometry(parts,w,h)
                    if(ClueRegionValidation.validateGeometryNormalized(
                            candidate,w,h,gridPoints).usable) {
                        newPreviews[k]=candidate
                        newPreviewReasons[k]=hafuch.reasons[label].orEmpty()
                    }
                }
            }
            DebugLog.i("LOCAL_OCR_HAFUCH","reviewOnly="+hafuch.proposals.size+
                " expected=28 noCanonicalWrite=true")
        }
""" + anchor
src=src.replace(anchor,replacement)
engine.write_text(src)
test=root/"app/src/test/java/com/example/hebrewcrossword/HafuchOcrWordReviewV214Test.kt"
assert not test.exists()
test.write_text("""package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class HafuchOcrWordReviewV214Test {
    @Test fun exactSeriesOnlyAndStrictNumbers() {
        assertTrue(HafuchOcrWordReviewV214.allowedSeries("HAFUCH_DEKEL"))
        for(id in listOf<String?>(null,"","YEDIOTH_DEKEL_WEEKLY",
            "YEDIOTH_MONDAY_DEKEL","YEDIOTH_WEDNESDAY_DEKEL","TARTEY_DEKEL"))
            assertFalse(HafuchOcrWordReviewV214.allowedSeries(id))
        assertEquals(23,HafuchOcrWordReviewV214.printedNumber("23."))
        assertEquals(1,HafuchOcrWordReviewV214.printedNumber("1:"))
        assertNull(HafuchOcrWordReviewV214.printedNumber("23"))
        assertNull(HafuchOcrWordReviewV214.printedNumber("(3)"))
        assertNull(HafuchOcrWordReviewV214.printedNumber("123."))
    }
    @Test fun printedLengthGrammar() {
        assertTrue(HafuchOcrWordReviewV214.printedLength("(3)"))
        assertTrue(HafuchOcrWordReviewV214.printedLength("(3,4,2);"))
        assertFalse(HafuchOcrWordReviewV214.printedLength("3"))
        assertFalse(HafuchOcrWordReviewV214.printedLength("23."))
    }
}
""")
print("HAFUCH_REVIEW_ONLY_STAGE",hafuch.name,test.name)
