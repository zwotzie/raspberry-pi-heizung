package de.zwotzie.heizung.ui.chart

import kotlin.math.abs

/** Rechnet Werte in Bildschirmkoordinaten um. */
object ChartScale {
    /**
     * Wertebereich für eine Serie. Ist die Spanne kleiner als [minSpan] (etwa bei
     * einer konstanten Linie), wird um die Mitte aufgeweitet, damit man etwas sieht.
     */
    fun range(values: List<Double?>, minSpan: Double): ClosedFloatingPointRange<Double> {
        val finite = values.filterNotNull().filter { it.isFinite() }
        val safeMinSpan = if (minSpan > 0.0) minSpan else 1.0

        if (finite.isEmpty()) return 0.0..safeMinSpan

        val low = finite.min()
        val high = finite.max()
        val span = high - low

        if (span >= safeMinSpan) return low..high

        val center = (low + high) / 2.0
        val half = safeMinSpan / 2.0
        return (center - half)..(center + half)
    }

    /** Bildschirm-y für [value]; [top] ist der obere, [bottom] der untere Rand. */
    fun yOf(value: Double, range: ClosedFloatingPointRange<Double>, top: Float, bottom: Float): Float {
        val span = range.endInclusive - range.start
        if (span <= 0.0 || abs(span) < 1e-9) return bottom

        val fraction = ((value - range.start) / span).coerceIn(0.0, 1.0)
        return (bottom - fraction * (bottom - top)).toFloat()
    }
}
