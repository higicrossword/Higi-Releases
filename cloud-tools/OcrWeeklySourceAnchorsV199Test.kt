package com.example.hebrewcrossword

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrWeeklySourceAnchorsV199Test {
    private fun word(text:String,x:Int,y:Int,width:Int=20,confidence:Int=93)=
        OcrSharedRowSplitterV161.Word(text,CropRect(x,y,x+width,y+15),confidence)

    @Test fun rejectedV1MayRecoverWithoutAnyPreviousCandidate() {
        val words=listOf(
            word("1.",288,172,12), word("ראש",220,172), word("אופוזיציה",100,172,100),
            word("2.",253,198,14),word("זמן",285,198,30),word("(3)",319,198,18),
            word("עם",205,198),word("מתח",140,198),
            word("3.",253,225,14),word("הגדרה",200,225))
        val result=OcrWeeklySourceAnchorsV199.inspect(words,
            setOf("V1","V2","V3"),1068,476)
        assertTrue("V1 must not require V184 accepted or V178 preview", "V1" in result.previews)
        val v1=result.previews.getValue("V1")
        assertTrue(v1.isNotEmpty())
        assertTrue(v1.any{it.left<=288 && it.right>=300 && it.top<=172})
        // The part of V1's continuation to the right of the 2 marker belongs to V1.
        assertTrue(v1.any{it.top<=198 && it.bottom>=213 && it.left>=267})
        assertTrue("V1 and V2 must not share the same word pixels",
            OcrWeeklySourceAnchorsV199.conflictingKeys(result.previews,words).isEmpty())
    }

    @Test fun sharedPrintedRowV3V4IsSplitByIndependentNumberBoxes() {
        val words=listOf(word("3.",253,225,14),word("מזמר",202,225,42),
            word("(4)",63,225,18),word("4.",26,225,14),word("משך",2,225,21),
            word("7.",253,279,14),word("המשך",190,279,46))
        val result=OcrWeeklySourceAnchorsV199.inspect(words,
            setOf("V3","V4","V7"),1068,476)
        assertTrue(result.previews.containsKey("V3"))
        assertTrue(result.previews.containsKey("V4"))
        assertTrue(OcrWeeklySourceAnchorsV199.conflictingKeys(result.previews,words).isEmpty())
    }

    @Test fun inlineNumberWithMissingDotIsReviewOnly() {
        val words=listOf(word("7.",253,279,14),word("תומך",120,279,45),
            word("8",23,279,12),word("משטרה",225,306,62),
            word("10.",244,333,24),word("קם",195,333))
        val result=OcrWeeklySourceAnchorsV199.inspect(words,
            setOf("V7","V8","V10"),1068,476)
        assertTrue(result.previews.containsKey("V8"))
        assertTrue(result.reasons.getValue("V8").contains("inferred=true"))
        assertTrue(result.reasons.getValue("V8").contains("NO_CANONICAL").not())
        assertTrue(result.reasons.getValue("V8").contains("no Canonical write"))
    }

    @Test fun overlappingLegacyCluesAreDetectedAcrossDifferentKeys() {
        val same=mapOf("H13" to listOf(CropRect(339,348,641,423)),
            "H14" to listOf(CropRect(360,377,609,423)))
        val conflicts=OcrWeeklySourceAnchorsV199.conflictingKeys(same,emptyList())
        assertTrue(conflicts["H13"]?.contains("H14")==true)
        assertTrue(conflicts["H14"]?.contains("H13")==true)
    }

    @Test fun differentDirectionsMaySharePixelsInIndependentColumns() {
        val same=mapOf("H1" to listOf(CropRect(330,172,652,201)),
            "V1" to listOf(CropRect(30,172,400,201)))
        assertTrue(OcrWeeklySourceAnchorsV199.conflictingKeys(same,emptyList()).isEmpty())
    }

    @Test fun noPrintedNumberDoesNotProduceGuessedCrop() {
        val result=OcrWeeklySourceAnchorsV199.inspect(listOf(word("טקסט",40,170,50)),
            setOf("V1","V2"),1068,476)
        assertTrue(result.previews.isEmpty())
        assertTrue(result.reasons["V1"].orEmpty().contains("NO_INDEPENDENT_PRINTED_START"))
    }

    @Test fun weeklyRoutingDoesNotCaptureTarteyOrHafuch() {
        assertEquals("YEDIOTH_DEKEL_WEEKLY",
            OcrSeriesProfilesV197.resolve("דקל בנו רביעי","YEDIOTH_WEDNESDAY_DEKEL:20261111").id)
        assertFalse(OcrSeriesProfilesV197.TARTEY.mondayBoundaryReview)
        assertFalse(OcrSeriesProfilesV197.HAFUCH.mondayBoundaryReview)
        assertEquals("TARTEY_DEKEL",OcrSeriesProfilesV197.resolve("תרתי משמע", "not-a-prefix").id)
    }
}