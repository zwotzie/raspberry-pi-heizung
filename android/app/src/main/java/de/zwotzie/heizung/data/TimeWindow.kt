package de.zwotzie.heizung.data

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.ceil
import kotlin.math.max

/** Sichtbarer Zeitausschnitt in UNIX-Sekunden. */
data class ViewWindow(val startSec: Long, val endSec: Long) {
    val spanSec: Long get() = endSec - startSec
}

/** Rechnet für Wischen, Zoomen und Achsenbeschriftung. */
object TimeWindow {
    private const val MIN_SPAN_SEC = 60L
    private const val DAY_LABELS = 6

    /** Fenster über alle Zeilen; `null`, wenn keine Zeile vorliegt. */
    fun of(rows: List<ChartRow>): ViewWindow? =
        if (rows.isEmpty()) {
            null
        } else {
            ViewWindow(rows.first().timestampSec, rows.last().timestampSec)
        }

    /** Verschiebt das Fenster, ohne die Grenzen zu verlassen und ohne die Breite zu ändern. */
    fun pan(window: ViewWindow, deltaSec: Long, bounds: ViewWindow): ViewWindow {
        val span = window.spanSec
        val maxStart = bounds.endSec - span
        if (maxStart <= bounds.startSec) return bounds
        val start = (window.startSec + deltaSec).coerceIn(bounds.startSec, maxStart)
        return ViewWindow(start, start + span)
    }

    /**
     * Ändert die Breite um [factor] (< 1 zoomt hinein), hält dabei [anchorSec] fest
     * und bleibt zwischen einer Minute und [bounds].
     */
    fun zoom(window: ViewWindow, factor: Double, anchorSec: Long, bounds: ViewWindow): ViewWindow {
        val span = window.spanSec
        if (span <= 0L) return bounds

        val boundsSpan = bounds.spanSec
        val newSpan = (span * factor).toLong()
            .coerceAtLeast(MIN_SPAN_SEC)
            .coerceAtMost(boundsSpan)

        val anchorOffset = (anchorSec - window.startSec).toDouble() / span
        val rawStart = anchorSec - (newSpan * anchorOffset).toLong()
        val start = rawStart.coerceIn(bounds.startSec, bounds.endSec - newSpan)
        return ViewWindow(start, start + newSpan)
    }

    /** Beschriftung der Zeitachse: Uhrzeiten am Tag, Wochentage in der Woche. */
    fun tickLabels(window: ViewWindow, period: Period, zone: ZoneId): List<Pair<Long, String>> {
        if (window.spanSec <= 0L) return emptyList()

        return when (period) {
            Period.DAY -> dayLabels(window, zone)
            Period.WEEK -> weekLabels(window, zone)
        }
    }

    private fun dayLabels(window: ViewWindow, zone: ZoneId): List<Pair<Long, String>> {
        val hours = max(1.0, window.spanSec / 3600.0)
        val stepHours = ceil(hours / DAY_LABELS).toLong().coerceAtLeast(1)
        val step = stepHours * 3600
        val formatter = DateTimeFormatter.ofPattern("HH:mm")

        val labels = mutableListOf<Pair<Long, String>>()
        var at = window.startSec
        while (at < window.endSec) {
            labels += at to Instant.ofEpochSecond(at).atZone(zone).format(formatter)
            at += step
        }
        return labels
    }

    private fun weekLabels(window: ViewWindow, zone: ZoneId): List<Pair<Long, String>> {
        val formatter = DateTimeFormatter.ofPattern("EEE", Locale.GERMAN)
        var day: LocalDate = Instant.ofEpochSecond(window.startSec).atZone(zone).toLocalDate()
        val lastDay: LocalDate = Instant.ofEpochSecond(window.endSec - 1).atZone(zone).toLocalDate()

        val labels = mutableListOf<Pair<Long, String>>()
        while (!day.isAfter(lastDay)) {
            val at = day.atStartOfDay(zone).toEpochSecond()
            if (at >= window.startSec && at < window.endSec) {
                labels += at to day.format(formatter)
            }
            day = day.plusDays(1)
        }
        return labels
    }
}
