package com.example.hebrewcrossword

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrSeriesProfilesV197Test {
    private fun row(i:Int,x:Int,y:Int,r:Int,b:Int)=
        OcrTextLocatorV033.Line(i,"printed clue",CropRect(x,y,r,b),91)
    private fun word(s:String,x:Int,y:Int,r:Int)=
        OcrSharedRowSplitterV161.Word(s,CropRect(x,y,r,y+15),93)
    private val lines=listOf(row(6,381,192,645,214),row(10,375,219,646,241),
        row(12,358,244,646,267),row(16,382,268,647,295))
    private val words=listOf(word("5.",627,196,641),word("6.",563,222,577),word("8.",518,248,533))
    private val legacy=mapOf("H5" to listOf(
        CropRect(380,191,645,217),CropRect(378,218,647,242),
        CropRect(356,244,647,266),CropRect(378,269,647,295)))
    @Test fun knownSeriesStayIndependent() {
        assertEquals("TARTEY_DEKEL",OcrSeriesProfilesV197.resolve("תרתי משמע - דקל בנו","TARTEY_DEKEL:20261023").id)
        assertEquals("HAFUCH_DEKEL",OcrSeriesProfilesV197.resolve("הפוך על הפוך","HAFUCH_DEKEL:20261106").id)
        assertEquals("YEDIOTH_MONDAY_DEKEL",OcrSeriesProfilesV197.resolve("דקל בנו שני","YEDIOTH_MONDAY_DEKEL:20261109").id)
        assertEquals("GENERIC",OcrSeriesProfilesV197.resolve("דקל בנו","unknown").id)
        assertFalse(OcrSeriesProfilesV197.TARTEY.mondayBoundaryReview)
        assertFalse(OcrSeriesProfilesV197.HAFUCH.mondayBoundaryReview)
    }
    @Test fun mondayProposalUsesPhysicalNumbersNotHardcodedRightEdge() {
        val r=OcrSeriesPreviewV197.inspect(OcrSeriesProfilesV197.MONDAY,
            legacy,lines,words,setOf("H5","H6","H8"),1056,474)
        assertTrue(r.reasons.toString(),r.previews.containsKey("H5"))
        val parts=r.previews.getValue("H5")
        assertEquals(2,parts.size)
        assertTrue(parts[1].left>=577)
        assertTrue(r.reasons.getValue("H5").contains("REVIEW_ONLY"))
    }
    @Test fun tarteyAndHafuchRemainByteUnchanged() {
        for(profile in listOf(OcrSeriesProfilesV197.TARTEY,OcrSeriesProfilesV197.HAFUCH,
            OcrSeriesProfilesV197.MAARIV,OcrSeriesProfilesV197.GENERIC)) {
            val r=OcrSeriesPreviewV197.inspect(profile,legacy,lines,words,
                setOf("H5","H6","H8"),1056,474)
            assertTrue(r.previews.isEmpty())
            assertTrue(r.reasons.isEmpty())
        }
    }
    @Test fun missingPrintedAnchorDoesNotGuess() {
        val r=OcrSeriesPreviewV197.inspect(OcrSeriesProfilesV197.MONDAY,
            legacy,lines,words.filterNot{it.text=="6."},setOf("H5","H6","H8"),1056,474)
        assertFalse(r.previews.containsKey("H5"))
    }
}