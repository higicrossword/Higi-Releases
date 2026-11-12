package com.example.hebrewcrossword

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrWeeklyFinalGeometryV201Test {
    private fun final(vararg p:CropRect)=OcrWeeklyFinalGeometryV201.Candidate(
        p.toList(),OcrWeeklyFinalGeometryV201.Origin.VERIFIED_FINAL)
    private fun fresh(vararg p:CropRect)=OcrWeeklyFinalGeometryV201.Candidate(
        p.toList(),OcrWeeklyFinalGeometryV201.Origin.SOURCE_ANCHORED_REVIEW)
    private fun legacy(vararg p:CropRect)=OcrWeeklyFinalGeometryV201.Candidate(
        p.toList(),OcrWeeklyFinalGeometryV201.Origin.REJECTED_LEGACY_REVIEW)
    private fun word(text:String,x:Int,y:Int,conf:Int=92)=OcrSharedRowSplitterV161.Word(
        text,CropRect(x,y,x+14,y+16),conf)

    @Test fun fourNovH11RejectedLegacyCannotVetoFinalH9OrNewH13(){
        // Original printed image ~1047x478; H11 old broad source area.
        val inp=linkedMapOf(
            "H9" to final(CropRect(375,292,639,320)),
            "H11" to legacy(CropRect(358,292,651,371)),
            "H13" to fresh(CropRect(389,345,541,371),CropRect(553,375,639,397)))
        val r=OcrWeeklyFinalGeometryV201.inspect(inp,listOf(word("9.",623,300),word("13.",517,352)),1047,668)
        assertTrue(r.demoteVerified.isEmpty())
        assertFalse(r.reasons.containsKey("H9"))
        assertFalse(r.reasons.containsKey("H13"))
        assertTrue(r.reasons.getValue("H11").any{it.contains("OLD_REJECTED_BOUND")})
    }
    @Test fun fourNovH8OverlappingPhysicalLinesAreBlocking(){
        val inp=mapOf("H8" to final(CropRect(404,246,457,267),CropRect(361,258,698,293)))
        val r=OcrWeeklyFinalGeometryV201.inspect(inp,emptyList(),1047,668)
        assertTrue("H8" in r.demoteVerified)
        assertTrue(r.reasons.getValue("H8").any{it.contains("SELF_OVERLAP")})
        assertTrue(r.reasons.getValue("H8").any{it.contains("GRID_INTRUSION")})
    }
    @Test fun trimFreshAcrossAtActualGridBoundaryNotFixed065Profile(){
        val input=listOf(CropRect(404,246,457,267),CropRect(361,258,698,293))
        val trim=OcrWeeklyFinalGeometryV201.clipFreshAcross("H8",input,668,1047)!!
        assertEquals(666,trim[1].right)
        assertEquals(457,trim[0].right)
        assertTrue(OcrWeeklyFinalGeometryV201.clipFreshAcross("H8",listOf(CropRect(670,260,699,285)),668,1047)==null)
        assertEquals(input,OcrWeeklyFinalGeometryV201.clipFreshAcross("V8",input,668,1047))
        assertEquals(input,OcrWeeklyFinalGeometryV201.clipFreshAcross("H8",input,null,1047))
    }
    @Test fun mondayNarrowNumbersAndSeparatedPiecesNotMistakenForOverlap(){
        val inp=mapOf("V2" to fresh(CropRect(76,169,93,189),CropRect(156,194,307,215)),
            "V3" to fresh(CropRect(52,191,153,213),CropRect(161,220,307,243)))
        val r=OcrWeeklyFinalGeometryV201.inspect(inp,emptyList(),1068,675)
        assertTrue(r.demoteVerified.isEmpty())
        assertTrue(r.reasons.isEmpty())
    }
    @Test fun twoTrustedCluesWithSameOcrWordCannotBothBeApproved(){
        val inp=mapOf("V4" to final(CropRect(20,222,145,240),CropRect(80,245,305,267)),
            "V7" to final(CropRect(45,245,296,283)))
        val r=OcrWeeklyFinalGeometryV201.inspect(inp,listOf(word("7.",75,248)),1068,675)
        assertEquals(setOf("V4","V7"),r.demoteVerified)
        assertTrue(r.reasons.getValue("V4").any{it.contains("CROSS_CLUE")})
    }
    @Test fun oldRejectedV2V7DoNotHideFourReviewedClues(){
        val inp=mapOf("V1" to final(CropRect(97,163,302,190)),
            "V2" to legacy(CropRect(40,164,316,215)),
            "V3" to fresh(CropRect(52,191,150,213),CropRect(161,219,304,243)),
            "V4" to fresh(CropRect(29,221,158,239),CropRect(90,246,307,267)),
            "V7" to legacy(CropRect(29,246,317,294)))
        val r=OcrWeeklyFinalGeometryV201.inspect(inp,emptyList(),1068,675)
        assertTrue(r.demoteVerified.isEmpty())
        assertFalse(r.reasons.containsKey("V1"))
        assertTrue(r.reasons.keys.containsAll(listOf("V2","V7")))
    }
    @Test fun unprovenGridCoordinatesDoNotBecomeAnInventedBoundary(){
        val p=listOf(CropRect(350,230,690,260))
        assertEquals(p,OcrWeeklyFinalGeometryV201.clipFreshAcross("H8",p,100,1047))
        assertEquals(p,OcrWeeklyFinalGeometryV201.clipFreshAcross("H8",p,990,1047))
        assertTrue(OcrWeeklyFinalGeometryV201.inspect(mapOf("H8" to fresh(*p.toTypedArray())),
            emptyList(),1047,100).reasons.isEmpty())
    }
    @Test fun horizontalAndVerticalPhysicalAreasAreNotCrossClueDuplicates(){
        val r=OcrWeeklyFinalGeometryV201.inspect(mapOf(
            "H1" to final(CropRect(70,170,270,188)),
            "V1" to final(CropRect(70,170,270,188))),listOf(word("1.",70,170)),1047,null)
        assertTrue(r.reasons.isEmpty())
    }
    @Test fun sourceReviewedAndValidTrustedHaveNoAutomaticVetoFromGeometryOnly(){
        val r=OcrWeeklyFinalGeometryV201.inspect(mapOf(
            "H9" to final(CropRect(400,292,630,320)),
            "H11" to fresh(CropRect(400,292,630,320))),emptyList(),1047,null)
        assertTrue(r.demoteVerified.isEmpty())
        assertTrue(r.reasons.containsKey("H9"))
    }
    @Test fun retainedSeriesRoutingIsUnchanged(){
        assertEquals("TARTEY_DEKEL",OcrSeriesProfilesV197.resolve("תרתי משמע","").id)
        assertEquals("HAFUCH_DEKEL",OcrSeriesProfilesV197.resolve("הפוך על הפוך","").id)
        assertEquals("YEDIOTH_DEKEL_WEEKLY",OcrSeriesProfilesV197.resolve("דקל בנו שני","").id)
        assertEquals("YEDIOTH_DEKEL_WEEKLY",OcrSeriesProfilesV197.resolve("דקל בנו רביעי","").id)
    }
}