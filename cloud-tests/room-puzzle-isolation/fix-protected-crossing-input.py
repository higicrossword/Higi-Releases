#!/usr/bin/env python3
"""Isolated regression fix: blocked typing at already-solved crossing square."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'app/src/main/java/com/example/hebrewcrossword/CrosswordSession.kt'
s=p.read_text()
old="""            if(protected!=null){
                crossword.cell(p.first,p.second).letter=protected
                if(protected!=chars[charIndex].toString()) break
            }else{
                crossword.cell(p.first,p.second).letter=chars[charIndex].toString()
            }
            cellIndex++
            charIndex++
            nextIndex=cellIndex.coerceAtMost(cells.lastIndex)"""
new="""            if(protected!=null){
                crossword.cell(p.first,p.second).letter=protected
                if(protected!=chars[charIndex].toString()) {
                    // If the cursor arrived by automatic typing advancement,
                    // skip the fixed crossing without consuming this character.
                    // An explicitly selected fixed cell must reject a wrong key.
                    if(cellIndex==index && !autoAdvancedByTyping)break
                    cellIndex++
                    continue
                }
            }else{
                crossword.cell(p.first,p.second).letter=chars[charIndex].toString()
            }
            cellIndex++
            charIndex++
            nextIndex=cellIndex.coerceAtMost(cells.lastIndex)"""
assert s.count(old)==1,(p,s.count(old))
s=s.replace("    private var protectedCells: Map<Pair<Int,Int>,String> = emptyMap()",
"""    private var protectedCells: Map<Pair<Int,Int>,String> = emptyMap()
    private var autoAdvancedByTyping=false""")
s=s.replace("        finishComposition(); wordOverride = next",
"""        finishComposition(); autoAdvancedByTyping=false; wordOverride = next""")
s=s.replace("        finishComposition(); wordOverride=null",
"""        finishComposition(); autoAdvancedByTyping=false; wordOverride=null""")
s=s.replace("        lastTapToggledDirection=false\n        if ((r to c) in word)",
"""        autoAdvancedByTyping=false
        lastTapToggledDirection=false
        if ((r to c) in word)""")
s=s.replace("        lastTapToggledDirection=false\n        row=r; col=c;",
"""        autoAdvancedByTyping=false
        lastTapToggledDirection=false
        row=r; col=c;""")
s=s.replace("        if (charIndex > 0) { val next=cells[nextIndex]; row=next.first; col=next.second }",
"""        if (charIndex > 0) {
            val next=cells[nextIndex]; row=next.first; col=next.second
            autoAdvancedByTyping=true
        }""")
s=s.replace("        finishComposition(); lastTap=null\n        val cells=word;",
"""        finishComposition(); lastTap=null; autoAdvancedByTyping=false
        val cells=word;""")
s=s.replace("        finishComposition();if(row<0||col<0)return",
"""        finishComposition();autoAdvancedByTyping=false;if(row<0||col<0)return""")
s=s.replace("    fun move(delta: Int) { finishComposition(); val cells=word;",
"""    fun move(delta: Int) { finishComposition(); autoAdvancedByTyping=false; val cells=word;""")
p.write_text(s.replace(old,new))
t=root/'app/src/test/java/com/example/hebrewcrossword/CrosswordProtectedCrossingTypingRegressionTest.kt'
assert not t.exists()
t.write_text("""package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class CrosswordProtectedCrossingTypingRegressionTest {
    private fun setup():Pair<Crossword,CrosswordSession> {
        val cw=Crossword(2,5,MutableList(2){MutableList(5){Cell()}})
        cw.assignNumbers()
        val s=CrosswordSession(cw)
        assertTrue(s.select(0,4))
        assertEquals(Direction.HORIZONTAL,s.direction)
        return cw to s
    }

    @Test fun mismatchAtSolvedCrossingDoesNotEatKeystroke() {
        val (cw,s)=setup()
        s.commitIme("א")
        assertEquals("א",cw.cell(0,4).letter)
        s.setProtectedCells(mapOf((0 to 3) to "ב"))
        s.commitIme("ג")
        assertEquals("ב",cw.cell(0,3).letter)
        assertEquals("ג",cw.cell(0,2).letter)
        assertEquals(0 to 1,s.row to s.col)
        s.commitIme("ד")
        assertEquals("ד",cw.cell(0,1).letter)
    }

    @Test fun explicitlySelectedProtectedCrossingRejectsWrongLetterWithoutSkipping() {
        val (cw,s)=setup()
        s.setProtectedCells(mapOf((0 to 3) to "ב"))
        s.restoreSelection(0,3,Direction.HORIZONTAL)
        s.commitIme("ז")
        assertEquals("ב",cw.cell(0,3).letter)
        assertEquals("",cw.cell(0,2).letter)
        assertEquals(0 to 3,s.row to s.col)
    }

    @Test fun matchingProtectedCrossingConsumesMatchingLetter() {
        val (cw,s)=setup()
        s.setProtectedCells(mapOf((0 to 3) to "ב"))
        s.commitIme("א")
        s.commitIme("ב")
        assertEquals("ב",cw.cell(0,3).letter)
        assertEquals("",cw.cell(0,2).letter)
        assertEquals(0 to 2,s.row to s.col)
        s.commitIme("ג")
        assertEquals("ג",cw.cell(0,2).letter)
    }

    @Test fun skipsSeveralProtectedCrossingsAndNeverReplacesThem() {
        val (cw,s)=setup()
        s.setProtectedCells(mapOf((0 to 3) to "ב",(0 to 2) to "ג"))
        s.commitIme("א")
        s.commitIme("ד")
        assertEquals("ב",cw.cell(0,3).letter)
        assertEquals("ג",cw.cell(0,2).letter)
        assertEquals("ד",cw.cell(0,1).letter)
        assertEquals(0 to 0,s.row to s.col)
    }

    @Test fun unmatchedLastProtectedCellRemainsFixed() {
        val (cw,s)=setup()
        s.setProtectedCells(mapOf((0 to 0) to "ה"))
        for(ch in listOf("א","ב","ג","ד"))s.commitIme(ch)
        s.commitIme("ו")
        assertEquals("ה",cw.cell(0,0).letter)
        assertEquals(0 to 0,s.row to s.col)
    }

    @Test fun ordinaryNonProtectedInputStillAdvances() {
        val (cw,s)=setup()
        for(ch in listOf("א","ב","ג"))s.commitIme(ch)
        assertEquals(listOf("א","ב","ג"),listOf(cw.cell(0,4).letter,cw.cell(0,3).letter,cw.cell(0,2).letter))
        assertEquals(0 to 1,s.row to s.col)
    }
}
""")
print('PATCHED CrosswordSession.kt and added 5 targeted regression tests')
