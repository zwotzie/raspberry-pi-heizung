package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZoneId

class TimeWindowTicksTest {
    private val zone = ZoneId.of("Europe/Berlin")

    private fun dayStart(year: Int, month: Int, day: Int): Long =
        java.time.LocalDate.of(year, month, day).atStartOfDay(zone).toEpochSecond()

    @Test
    fun `eine stunde zoom hat mindestens vier beschriftungen`() {
        val start = dayStart(2026, 11, 11) + 14 * 3600
        val labels = TimeWindow.tickLabels(ViewWindow(start, start + 3600), Period.DAY, zone)
        assertTrue("nur ${labels.size} Labels", labels.size >= 4)
    }

    @Test
    fun `gezoomte woche hat stundenlabels`() {
        val start = dayStart(2026, 11, 5) + 12 * 3600
        val labels = TimeWindow.tickLabels(ViewWindow(start, start + 3 * 3600), Period.WEEK, zone)
        assertTrue("nur ${labels.size} Labels", labels.size >= 3)
    }

    @Test
    fun `rueckstellung im oktober ergibt keine doppelte zwei-uhr`() {
        val start = dayStart(2027, 10, 31)
        val end = start + 25 * 3600
        val labels = TimeWindow.tickLabels(ViewWindow(start, end), Period.DAY, zone)

        assertEquals(25 * 3600L, end - start)
        assertEquals(labels.size, labels.map { it.second }.toSet().size)
        assertTrue(labels.none { it.second == "02:00" })
        assertTrue(labels.size >= 4)
    }

    @Test
    fun `labels liegen auf runden zeiten`() {
        val start = dayStart(2026, 11, 11) + 14 * 60 + 37
        val labels = TimeWindow.tickLabels(ViewWindow(start, start + 86_400), Period.DAY, zone)
        assertTrue(labels.all { it.second.endsWith(":00") || it.second.endsWith(":30") })
    }
}
