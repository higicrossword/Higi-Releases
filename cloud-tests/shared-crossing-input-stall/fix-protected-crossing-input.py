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
                    // A fixed crossing has its own letter. The user is typing the
                    // next unsolved square: skip this protected cell without
                    // consuming the keystroke (otherwise keyboard appears frozen).
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
