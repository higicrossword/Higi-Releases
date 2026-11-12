package com.example.hebrewcrossword

import org.junit.Assert.assertEquals
import org.junit.Test

class AdminOcrSwipeTrackerTest {
    private fun tracker() = AdminOcrSwipeTracker(56f, 52f)

    @Test fun rightSwipeChangesToPreviousAfterManyMoves() {
        val g = tracker()
        g.down(40f, 90f)
        // This trace mimics the original production bug: ACTION_MOVE was overwriting
        // swipeStartX, leaving only 5px at ACTION_UP instead of 155px.
        assertEquals(-1, g.up(195f, 98f, true))
    }

    @Test fun leftSwipeChangesToNext() {
        val g = tracker(); g.down(210f, 90f)
        assertEquals(1, g.up(96f, 105f, true))
    }

    @Test fun verticalDragIsNotNavigation() {
        val g = tracker(); g.down(110f, 80f)
        assertEquals(0, g.up(95f, 210f, true))
    }

    @Test fun diagonalDragIsNotNavigation() {
        val g = tracker(); g.down(130f, 70f)
        assertEquals(0, g.up(35f, 127f, true))
    }

    @Test fun shortSwipeIsNotNavigation() {
        val g = tracker(); g.down(125f, 70f)
        assertEquals(0, g.up(87f, 75f, true))
    }

    @Test fun pinchNeverTriggersNavigationEvenAfterPointerLift() {
        val g = tracker(); g.down(40f, 70f); g.addPointer()
        assertEquals(0, g.up(240f, 76f, true))
    }

    @Test fun imagePanningHasPriorityOverNavigation() {
        val g = tracker(); g.down(45f, 70f)
        assertEquals(0, g.up(240f, 70f, false))
    }

    @Test fun cancelResetsGestureState() {
        val g = tracker(); g.down(40f, 90f); g.cancel()
        assertEquals(0, g.up(200f, 90f, true))
    }

    @Test fun trackerMayBeReusedAfterPinchAndCancel() {
        val g = tracker(); g.down(40f, 90f); g.addPointer()
        assertEquals(0, g.up(200f, 90f, true))
        g.down(200f, 90f)
        assertEquals(1, g.up(40f, 90f, true))
    }
}