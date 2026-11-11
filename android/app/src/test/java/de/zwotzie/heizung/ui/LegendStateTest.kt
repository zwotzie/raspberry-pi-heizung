package de.zwotzie.heizung.ui

import androidx.compose.ui.graphics.Color
import de.zwotzie.heizung.data.Catalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LegendStateTest {
    @Test
    fun `legende zeigt temperaturen dann zeilen dann digitale signale`() {
        val spec = Catalog.tabs[1]

        val entries = LegendEntries.of(spec)

        assertEquals(spec.temperatures.first(), entries.first().metric)
        assertEquals(spec.digital.last(), entries.last().metric)
        assertEquals(spec.temperatures.size + spec.rows.size + spec.digital.size, entries.size)
    }

    @Test
    fun `jeder eintrag hat farbe und anzeigenamen`() {
        LegendEntries.of(Catalog.tabs[0]).forEach {
            assertTrue(it.label.isNotBlank())
            assertNotEquals(Color.Unspecified, it.color)
        }
    }
}
