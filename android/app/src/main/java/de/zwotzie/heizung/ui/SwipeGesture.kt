package de.zwotzie.heizung.ui

import kotlin.math.abs

/** Erkennt horizontale Wischgesten und rechnet Reiter-Wechsel im Kreis. */
object SwipeGesture {
    private const val LONG_SWIPE_FRACTION = 1f / 3f
    private const val QUICK_SWIPE_FRACTION = 1f / 6f
    private const val QUICK_SWIPE_MS = 200L

    /** Richtung der Wischgeste: +1 weiter, -1 zurück, 0 keine. */
    fun direction(totalDx: Float, widthPx: Float, elapsedMs: Long): Int {
        if (widthPx <= 0f) return 0
        val distance = abs(totalDx)
        val longSwipe = distance >= widthPx * LONG_SWIPE_FRACTION
        val quickSwipe = distance >= widthPx * QUICK_SWIPE_FRACTION && elapsedMs <= QUICK_SWIPE_MS
        if (!longSwipe && !quickSwipe) return 0
        return if (totalDx < 0f) 1 else -1
    }
}

/** Nächster Reiter mit Umlauf: aus dem letzten wird wieder der erste. */
fun cycleTab(index: Int, delta: Int, count: Int): Int =
    if (count <= 0) 0 else Math.floorMod(index + delta, count)
