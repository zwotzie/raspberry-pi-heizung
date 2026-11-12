package de.zwotzie.heizung.ui.chart

import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor

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

    /**
     * Weitet [range] nach außen auf Vielfache von [step] auf, damit die
     * Gitterlinien auf runden Werten liegen und nicht am Rand kleben.
     */
    fun gridRange(range: ClosedFloatingPointRange<Double>, step: Double): ClosedFloatingPointRange<Double> {
        if (step <= 0.0) return range
        val low = floor(range.start / step) * step
        val high = ceil(range.endInclusive / step) * step
        return low..high
    }

    /** Alle Gitterwerte innerhalb von [range], beginnend beim ersten Vielfachen von [step]. */
    fun gridValues(range: ClosedFloatingPointRange<Double>, step: Double): List<Double> {
        if (step <= 0.0) return emptyList()
        val values = mutableListOf<Double>()
        var value = ceil(range.start / step) * step
        while (value <= range.endInclusive + step * 1e-9) {
            values += value
            value += step
        }
        return values
    }

    /** Bildschirm-y für [value]; [top] ist der obere, [bottom] der untere Rand. */
    fun yOf(value: Double, range: ClosedFloatingPointRange<Double>, top: Float, bottom: Float): Float {
        val span = range.endInclusive - range.start
        if (span <= 0.0 || abs(span) < 1e-9) return bottom

        val fraction = ((value - range.start) / span).coerceIn(0.0, 1.0)
        return (bottom - fraction * (bottom - top)).toFloat()
    }
}
