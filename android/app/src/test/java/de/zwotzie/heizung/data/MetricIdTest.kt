package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Test

class MetricIdTest {
    @Test
    fun `reihenfolge entspricht der api`() {
        assertEquals(28, MetricId.entries.size)
        assertEquals("kessel_rl", MetricId.entries[0].apiName)
        assertEquals("solar_ladepumpe_drehzahl", MetricId.entries[16].apiName)
        assertEquals("d_heizung_pumpe", MetricId.entries[17].apiName)
        assertEquals("heizung_an", MetricId.entries[27].apiName)
    }

    @Test
    fun `keine doppelten api-namen`() {
        assertEquals(28, MetricId.entries.map { it.apiName }.toSet().size)
    }
}
