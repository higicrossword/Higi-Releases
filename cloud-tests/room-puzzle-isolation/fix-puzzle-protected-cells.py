#!/usr/bin/env python3
"""Fix protected solution leakage when activating another puzzle."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'app/src/main/java/com/example/hebrewcrossword/CrosswordView.kt'
s=p.read_text()
old="""    var crossword: Crossword? = null
        set(v) {
            field=v; session=v?.let(::CrosswordSession); session?.setProtectedCells(protectedSolutionCells)
            applyLockedPath(); requestLayout(); refresh()
        }"""
new="""    var crossword: Crossword? = null
        set(v) {
            // Fixed letters are scoped to a puzzle, never to grid coordinates alone.
            // A new crossword may have exactly the same dimensions as the old one:
            // replaying protectedSolutionCells would copy solved answers into it.
            val oldPuzzleId=field?.puzzleId
            protectedSolutionCells=PuzzleProtectedCellsScope.forPuzzle(
                oldPuzzleId,v?.puzzleId,protectedSolutionCells)
            if(oldPuzzleId!=v?.puzzleId){
                lockedSolvedEntries=emptySet()
                solvedByLabels=emptyMap()
                sharedFocusCells=emptySet()
                remoteHighlightCells=emptySet()
                letterColors=emptyMap()
                answerMarks=emptyMap()
                boldLetterCells=emptySet()
                compoundEntries=emptyList()
                inputLockedToEntry=null
                inputLockedEntries=emptyList()
            }
            field=v; session=v?.let(::CrosswordSession); session?.setProtectedCells(protectedSolutionCells)
            applyLockedPath(); requestLayout(); refresh()
        }"""
assert s.count(old)==1,(p,s.count(old))
p.write_text(s.replace(old,new))
helper=root/'app/src/main/java/com/example/hebrewcrossword/PuzzleProtectedCellsScope.kt'
assert not helper.exists()
helper.write_text("""package com.example.hebrewcrossword

/** A protected crossing is valid only inside the puzzle that issued it. */
internal object PuzzleProtectedCellsScope {
    fun forPuzzle(
        previousPuzzleId:String?,
        nextPuzzleId:String?,
        protected:Map<Pair<Int,Int>,String>
    ):Map<Pair<Int,Int>,String> =
        if(previousPuzzleId!=null && previousPuzzleId==nextPuzzleId)protected else emptyMap()
}
""")
test=root/'app/src/test/java/com/example/hebrewcrossword/PuzzleProtectedCellsScopeTest.kt'
assert not test.exists()
test.write_text("""package com.example.hebrewcrossword

import org.junit.Assert.*
import org.junit.Test

class PuzzleProtectedCellsScopeTest {
    private val oldLetters=mapOf((0 to 0) to "א",(1 to 1) to "ב")

    @Test fun switchToAnotherPuzzleSameGridClearsOldLetters() {
        assertTrue(PuzzleProtectedCellsScope.forPuzzle("old","new",oldLetters).isEmpty())
    }

    @Test fun reopeningTheSamePuzzleCanKeepItsOwnProtection() {
        assertEquals(oldLetters,PuzzleProtectedCellsScope.forPuzzle("same","same",oldLetters))
    }

    @Test fun exitToHomeDoesNotKeepProtection() {
        assertTrue(PuzzleProtectedCellsScope.forPuzzle("old",null,oldLetters).isEmpty())
    }

    @Test fun initialOpenDoesNotInheritProtection() {
        assertTrue(PuzzleProtectedCellsScope.forPuzzle(null,"new",oldLetters).isEmpty())
    }

    @Test fun sessionLeakReproductionShowsWhyProtectionMustBeReset() {
        val cw=Crossword(3,3,MutableList(3){MutableList(3){Cell()}})
        val session=CrosswordSession(cw)
        session.setProtectedCells(oldLetters)
        assertEquals("א",cw.cell(0,0).letter)
        assertEquals("ב",cw.cell(1,1).letter)
        val fresh=Crossword(3,3,MutableList(3){MutableList(3){Cell()}})
        val incoming=PuzzleProtectedCellsScope.forPuzzle("previous","fresh",oldLetters)
        CrosswordSession(fresh).setProtectedCells(incoming)
        assertEquals("",fresh.cell(0,0).letter)
        assertEquals("",fresh.cell(1,1).letter)
    }
}
""")
print("CROSSWORD_PROTECTION_SCOPE_PATCH_READY")

# Keep shared-room UI attribution and locks separate even when the puzzle is
# reactivated through an existing library record or the remote letters are late.
main=root/'app/src/main/java/com/example/hebrewcrossword/MainActivity.kt'
src=main.read_text()
old="""        chatMessages=emptyList();chatKnownIds.clear();chatInitialized=false;chatUnread=0;solvedAttributions=emptyMap();sharingParticipants=emptyList();sharedRemoteCells=emptyMap();updateChatButton(true);updateStatsButton(true);updateSolutionsBadge();updateAnswerColors()"""
new="""        chatMessages=emptyList();chatKnownIds.clear();chatInitialized=false;chatUnread=0;solvedAttributions=emptyMap();sharingParticipants=emptyList();sharedRemoteCells=emptyMap()
        // A new room must never inherit answer locks/attribution from the prior room,
        // even before Firebase supplies the new room's first onSolvedBy snapshot.
        board.lockedSolvedEntries=emptySet()
        board.solvedByLabels=emptyMap()
        board.setProtectedSolutionCells(emptyMap())
        updateChatButton(true);updateStatsButton(true);updateSolutionsBadge();updateAnswerColors()"""
assert src.count(old)==1,("connectShared room reset anchor",src.count(old))
main.write_text(src.replace(old,new))
print("SHARED_ROOM_UI_RESET_PRECONNECT_APPLIED")
