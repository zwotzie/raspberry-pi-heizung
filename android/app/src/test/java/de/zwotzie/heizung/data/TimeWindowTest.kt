package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.ZoneId

class TimeWindowTest {
    private val zone = ZoneId.of("Europe/Berlin")
    private val bounds = ViewWindow(1_700_000_000, 1_700_086_400)

    @Test
    fun `wischen stoppt am rand`() {
        val window = ViewWindow(1_700_000_000, 1_700_043_200)

        val left = TimeWindow.pan(window, -99_999_999, bounds)
        assertEquals(bounds.startSec, left.startSec)

        val right = TimeWindow.pan(window, 99_999_999, bounds)
        assertEquals(bounds.endSec, right.endSec)
        assertEquals(window.endSec - window.startSec, right.endSec - right.startSec)
    }

    @Test
    fun `wischen in der mitte verschiebt um genau den betrag`() {
        val window = ViewWindow(1_700_010_000, 1_700_053_200)
        val moved = TimeWindow.pan(window, 1_000, bounds)
        assertEquals(window.startSec + 1_000, moved.startSec)
        assertEquals(window.endSec + 1_000, moved.endSec)
    }

    @Test
    fun `zoomen haelt den ankerpunkt`() {
        val zoomed = TimeWindow.zoom(
            ViewWindow(0, 86_400),
            factor = 0.5,
            anchorSec = 43_200,
            bounds = ViewWindow(0, 86_400),
        )
        assertEquals(21_600, zoomed.startSec)
        assertEquals(64_800, zoomed.endSec)
    }

    @Test
    fun `zoom wird nicht kleiner als eine minute und nicht groesser als bounds`() {
        val tiny = TimeWindow.zoom(ViewWindow(0, 86_400), 0.0001, 43_200, ViewWindow(0, 86_400))
        assertTrue(tiny.endSec - tiny.startSec >= 60)

        val huge = TimeWindow.zoom(ViewWindow(0, 86_400), 100.0, 43_200, ViewWindow(0, 86_400))
        assertEquals(0, huge.startSec)
        assertEquals(86_400, huge.endSec)
    }

    @Test
    fun `tagsbeschriftung ist stundenweise in berliner zeit`() {
        val labels = TimeWindow.tickLabels(bounds, Period.DAY, zone)
        assertTrue(labels.size in 4..8)
        assertTrue(labels.all { it.second.matches(Regex("""\d{2}:\d{2}""")) })
    }

    @Test
    fun `zeitumstellung ergibt 23-stunden-tag ohne zwei-uhr-label`() {
        val start = LocalDate.of(2025, 3, 30).atStartOfDay(zone).toEpochSecond()
        val end = LocalDate.of(2025, 3, 31).atStartOfDay(zone).toEpochSecond()

        assertEquals(23 * 3600L, end - start)
        val labels = TimeWindow.tickLabels(ViewWindow(start, end), Period.DAY, zone)
        assertEquals("00:00", labels.first().second)
        assertTrue(labels.none { it.second == "02:00" })
    }

    @Test
    fun `woche hat einen label pro tag`() {
        val start = LocalDate.of(2026, 11, 5).atStartOfDay(zone).toEpochSecond()
        val end = start + 7 * 86_400L

        val labels = TimeWindow.tickLabels(ViewWindow(start, end), Period.WEEK, zone)
        assertEquals(7, labels.size)
        assertTrue(labels.first().second.startsWith("Do"))
    }

    @Test
    fun `leere reihen ergeben kein fenster`() {
        assertEquals(null, TimeWindow.of(emptyList()))
    }
}
