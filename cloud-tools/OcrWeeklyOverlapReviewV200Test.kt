package com.example.hebrewcrossword

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrWeeklyOverlapReviewV200Test {
    private fun word(text:String,x:Int,y:Int,w:Int=14,confidence:Int=95)=
        OcrSharedRowSplitterV161.Word(text,CropRect(x,y,x+w,y+15),confidence)
    private fun prev(vararg parts:CropRect)=OcrWeeklyOverlapReviewV200.Candidate(
        parts.toList(),OcrWeeklyOverlapReviewV200.Origin.LEGACY_PREVIEW)
    private fun fresh(vararg parts:CropRect)=OcrWeeklyOverlapReviewV200.Candidate(
        parts.toList(),OcrWeeklyOverlapReviewV200.Origin.SOURCE_ANCHORED)
    private fun accepted(vararg parts:CropRect)=OcrWeeklyOverlapReviewV200.Candidate(
        parts.toList(),OcrWeeklyOverlapReviewV200.Origin.ACCEPTED)
    @Test fun mondayV2LegacyMustNotHideV1OrV3() {
        // From 09.11 source coordinates (1068x476), old V2 spans both peers.
        val x=linkedMapOf(
            "V1" to accepted(CropRect(97,163,302,189)),
            "V2" to prev(CropRect(40,164,316,215)),
            "V3" to fresh(CropRect(52,191,150,213),CropRect(161,219,304,243)))
        val out=OcrWeeklyOverlapReviewV200.assess(x,listOf(word("1.",288,172),word("3.",134,196)))
        assertEquals(x.keys,out.candidates.keys)
        assertTrue(out.warnings.containsKey("V2"))
        assertTrue(out.warnings.getValue("V2").any{it.peer=="V1"})
        assertTrue(out.warnings.getValue("V2").any{it.peer=="V3"})
        assertTrue(out.warnings.getValue("V1").any{it.peerOrigin==OcrWeeklyOverlapReviewV200.Origin.LEGACY_PREVIEW})
    }
    @Test fun mondayV7LegacyVsV4SourceAnchoredKeepsBothOnScreen() {
        val map=mapOf("V4" to fresh(CropRect(29,221,158,239),CropRect(90,246,307,267)),
            "V7" to prev(CropRect(29,246,317,294)))
        val result=OcrWeeklyOverlapReviewV200.assess(map,listOf(word("7.",69,248)))
        assertEquals(2,result.candidates.size)
        assertTrue(result.warnings.containsKey("V7"))
        assertTrue(result.warnings.containsKey("V4"))
    }
    @Test fun wednesdayV4AndV8RemainVisibleRatherThanDisappearing() {
        val map=mapOf(
            "V2" to fresh(CropRect(14,192,268,213),CropRect(274,219,306,235)),
            "V4" to prev(CropRect(9,211,316,291)),
            "V7" to fresh(CropRect(39,269,270,293)),
            "V8" to prev(CropRect(12,269,316,341)),
            "V10" to fresh(CropRect(30,317,270,342)))
        val out=OcrWeeklyOverlapReviewV200.assess(map,emptyList())
        assertEquals(5,out.candidates.size)
        assertTrue(out.warnings.getValue("V4").isNotEmpty())
        assertTrue(out.warnings.getValue("V8").isNotEmpty())
        assertTrue(OcrWeeklyOverlapReviewV200.detail(out.warnings.getValue("V4")).contains("GEOMETRIC_ONLY_UNVERIFIED"))
    }
    @Test fun conflictsInChainDoNotCascadeDeletion() {
        val map=linkedMapOf("V1" to fresh(CropRect(0,0,50,30)),
            "V2" to prev(CropRect(25,0,75,30)),
            "V3" to fresh(CropRect(50,0,100,30)))
        val w=OcrWeeklyOverlapReviewV200.assess(map,listOf(word("ט",30,0),word("ט",60,0)))
        assertEquals(3,w.candidates.size)
        assertTrue(w.warnings.containsKey("V1"))
        assertTrue(w.warnings.containsKey("V3"))
        assertFalse(w.warnings.getValue("V1").any{it.peer=="V3"})
    }
    @Test fun independentDirectionsAndTouchingBoxesAreNotConflicts() {
        val map=mapOf("H1" to fresh(CropRect(0,0,80,30)),
            "V1" to fresh(CropRect(0,0,80,30)),
            "H5" to fresh(CropRect(80,0,140,30)))
        assertTrue(OcrWeeklyOverlapReviewV200.assess(map,emptyList()).warnings.isEmpty())
    }
    @Test fun sharedWordProvesPotentialDuplicateDespiteModestGeometry() {
        val map=mapOf("H13" to fresh(CropRect(300,300,500,330)),
            "H14" to prev(CropRect(490,300,550,330)))
        val w=OcrWeeklyOverlapReviewV200.assess(map,listOf(word("14.",491,302,12)))
        assertTrue(w.warnings.getValue("H13").single().sharedOcrWords>=1)
        assertTrue(OcrWeeklyOverlapReviewV200.detail(w.warnings.getValue("H13")).contains("SHARED_OCR_WORD_CENTERS"))
    }
    @Test fun unrelatedSmallGeometricTouchDoesNotTriggerFalseAlarm() {
        val map=mapOf("V4" to fresh(CropRect(0,0,100,40)),
            "V7" to fresh(CropRect(91,32,141,72)))
        assertTrue(OcrWeeklyOverlapReviewV200.assess(map,emptyList()).warnings.isEmpty())
    }
    @Test fun printedStartOnlyCanRemainVisibleForAdminReview() {
        val parts=listOf(CropRect(24,225,42,240),CropRect(80,249,270,267))
        assertTrue(OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview("V4",parts,
            listOf(word("4.",26,225)),"physical-row-1:too-narrow-px:18"))
        assertFalse(OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview("V4",parts,
            listOf(word("8.",26,225)),"physical-row-1:too-narrow-px:18"))
    }
    @Test fun nonNumberOrOtherGeometryErrorsNeverBypassValidation() {
        val parts=listOf(CropRect(24,225,42,240),CropRect(80,249,270,267))
        assertFalse(OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview("V4",parts,
            listOf(word("4.",26,225)),"physical-row-1:center-inside-grid"))
        assertFalse(OcrWeeklyOverlapReviewV200.narrowNumberOnlyPreview("V4",listOf(parts.first()),
            listOf(word("4.",26,225)),"physical-row-1:too-narrow-px:18"))
    }
    @Test fun existingTarteyAndHafuchRoutingRemainsIsolated() {
        assertEquals("TARTEY_DEKEL",OcrSeriesProfilesV197.resolve("תרתי משמע","").id)
        assertEquals("HAFUCH_DEKEL",OcrSeriesProfilesV197.resolve("הפוך על הפוך","").id)
        assertEquals("YEDIOTH_DEKEL_WEEKLY",OcrSeriesProfilesV197.resolve("דקל בנו שני","").id)
        assertEquals("YEDIOTH_DEKEL_WEEKLY",OcrSeriesProfilesV197.resolve("דקל בנו רביעי","").id)
    }
}