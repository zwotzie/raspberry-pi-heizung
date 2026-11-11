package de.zwotzie.heizung.data

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Sichtbarer Zeitausschnitt in UNIX-Sekunden. */
data class ViewWindow(val startSec: Long, val endSec: Long) {
    val spanSec: Long get() = endSec - startSec
}

/** Rechnet für Wischen, Zoomen und Achsenbeschriftung. */
object TimeWindow {
    private const val MIN_SPAN_SEC = 60L
    private const val TARGET_LABELS = 6
    private const val LAST_STEP_SEC = 86_400L
    private val STEPS_SEC = longArrayOf(60, 120, 300, 600, 900, 1_800, 3_600, 7_200, 14_400, 21_600, 43_200, 86_400)

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

        return if (period == Period.WEEK && window.spanSec >= 2 * LAST_STEP_SEC) {
            weekLabels(window, zone)
        } else {
            dayLabels(window, zone)
        }
    }

    private fun dayLabels(window: ViewWindow, zone: ZoneId): List<Pair<Long, String>> {
        val step = STEPS_SEC.firstOrNull { it >= window.spanSec / TARGET_LABELS } ?: LAST_STEP_SEC
        val formatter = DateTimeFormatter.ofPattern("HH:mm")

        val labels = mutableListOf<Pair<Long, String>>()
        var cursor = alignDown(Instant.ofEpochSecond(window.startSec).atZone(zone), step)
        val stepDuration = java.time.Duration.ofSeconds(step)

        while (cursor.toEpochSecond() < window.endSec) {
            val at = cursor.toEpochSecond()
            if (at >= window.startSec) labels += at to cursor.format(formatter)
            cursor = cursor.toLocalDateTime().plus(stepDuration).atZone(zone)
        }
        return labels
    }

    /** Rundet auf die letzte volle [step]-Grenze der lokalen Uhrzeit ab. */
    private fun alignDown(zdt: java.time.ZonedDateTime, step: Long): java.time.ZonedDateTime {
        val secondOfDay = zdt.toLocalTime().toSecondOfDay().toLong()
        val floored = (secondOfDay / step) * step
        return zdt.toLocalDate().atTime(java.time.LocalTime.ofSecondOfDay(floored)).atZone(zdt.zone)
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
