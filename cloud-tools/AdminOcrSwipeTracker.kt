package com.example.hebrewcrossword

import kotlin.math.abs

/** Single-finger, displacement-based navigation. Pointer moves never reset the origin.
 *  Returns -1 for right swipe (previous), +1 for left swipe (next), or 0 for no navigation.
 *  The view must independently decide whether the image is horizontally pannable.
 */
internal class AdminOcrSwipeTracker(
    private val minHorizontalPx: Float,
    private val maxVerticalPx: Float,
) {
    private var downX = 0f
    private var downY = 0f
    private var active = false
    private var multiTouch = false

    fun down(x: Float, y: Float) {
        downX = x
        downY = y
        active = true
        multiTouch = false
    }

    fun addPointer() { multiTouch = true }

    fun up(x: Float, y: Float, navigationAllowed: Boolean): Int {
        if (!active) return 0
        val dx = x - downX
        val dy = y - downY
        val direction = if (navigationAllowed && !multiTouch &&
            abs(dx) >= minHorizontalPx && abs(dy) <= maxVerticalPx &&
            abs(dx) >= abs(dy) * 1.5f
        ) {
            if (dx > 0f) -1 else 1
        } else 0
        cancel()
        return direction
    }

    fun cancel() {
        active = false
        multiTouch = false
    }
}