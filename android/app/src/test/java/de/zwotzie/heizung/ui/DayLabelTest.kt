package de.zwotzie.heizung.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class DayLabelTest {
    private val heute = LocalDate.of(2026, 11, 14)

    @Test
    fun `heutiger tag heisst heute`() {
        assertEquals("Heute", DayLabel.of(heute, heute))
    }

    @Test
    fun `anderer tag zeigt wochentag und datum`() {
        val label = DayLabel.of(heute.minusDays(1), heute)

        assertTrue(label, label.startsWith("Fr"))
        assertTrue(label, label.contains("13"))
        assertTrue(label, label.contains("Nov"))
    }
}
