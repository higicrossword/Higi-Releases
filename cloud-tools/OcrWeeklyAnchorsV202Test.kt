package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class OcrWeeklyAnchorsV202Test {
    private fun w(s:String,x:Int,y:Int,confidence:Int=92):OcrSharedRowSplitterV161.Word =
        OcrSharedRowSplitterV161.Word(s,CropRect(x,y,x+21,y+15),confidence)
    private fun content(x:Int,y:Int)=w("word",x,y,90)
    private val width=1055
    private val height=480
    @Test fun contextualWeakElevenAndThirteenRecoverInRightOrder(){
        val words=listOf(w("1.",627,181),content(365,181),w("9.",598,314),content(370,314),
            w("1",618,341,54),content(390,341),w("3",617,367,27),content(390,367),
            w("14.",583,394),content(390,394),content(390,421))
        val found=OcrWeeklySourceAnchorsV199.inspect(words,setOf("H1","H9","H11","H13","H14"),width,height)
        assertTrue("H11 must be contextually anchored: ${found.reasons}", "H11" in found.previews)
        assertTrue("H13 weak suffix must be bounded: ${found.reasons}", "H13" in found.previews)
        assertTrue(found.reasons["H11"].orEmpty().contains("inferred=true"))
        assertTrue(found.reasons["H13"].orEmpty().contains("inferred=true"))
    }
    @Test fun weakSuffixWithoutTwoReliableNeighborsIsRejected(){
        val words=listOf(w("3",617,367,27),content(390,367),w("14.",583,394),content(390,394))
        val found=OcrWeeklySourceAnchorsV199.inspect(words,setOf("H11","H13","H14"),width,height)
        assertFalse("H13" in found.previews)
    }
    @Test fun duplicateWeakSuffixDoesNotGuess(){
        val words=listOf(w("11.",598,341),content(390,341),w("3",612,367,27),
            w("3",635,367,30),content(390,367),w("14.",583,394),content(390,394))
        val found=OcrWeeklySourceAnchorsV199.inspect(words,setOf("H11","H13","H14"),width,height)
        assertFalse("H13" in found.previews)
    }
    @Test fun exactExistingStartsRemainPreferred(){
        val words=listOf(w("1.",627,181),content(390,181),w("9.",598,314),content(390,314),
            w("11.",618,341),content(390,341),w("13.",617,367),content(390,367),
            w("14.",583,394),content(390,394))
        val found=OcrWeeklySourceAnchorsV199.inspect(words,setOf("H1","H9","H11","H13","H14"),width,height)
        assertFalse(found.reasons["H11"].orEmpty().contains("inferred=true"))
        assertFalse(found.reasons["H13"].orEmpty().contains("inferred=true"))
    }
}