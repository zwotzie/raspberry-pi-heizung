package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CatalogTest {
    @Test
    fun `vier reiter in fester reihenfolge`() {
        assertEquals(listOf("Puffer", "Solar", "Heizung", "Erzeuger"), Catalog.tabs.map { it.title })
    }

    @Test
    fun `puffer zeigt sieben temperaturen ohne digitale baender`() {
        val puffer = Catalog.tabs.first()
        assertEquals(7, puffer.temperatures.size)
        assertTrue(puffer.digital.isEmpty())
        assertEquals(MetricId.SPEICHER_1_KOPF, puffer.temperatures[2])
    }

    @Test
    fun `jede metrik hat einen anzeigenamen und eine einheit`() {
        MetricId.entries.forEach { assertTrue(Catalog.spec(it).label.isNotBlank()) }
        assertEquals(Unit.WATT_PER_M2, Catalog.spec(MetricId.SOLAR_STRAHLUNG).unit)
        assertEquals(Unit.PERCENT, Catalog.spec(MetricId.SOLAR_LADEPUMPE_DREHZAHL).unit)
        assertEquals(Unit.CELSIUS, Catalog.spec(MetricId.SPEICHER_1_KOPF).unit)
    }

    @Test
    fun `keine metrik fehlt in den reitern`() {
        val used = Catalog.tabs.flatMap { it.temperatures + it.rows + it.digital }.toSet()
        assertEquals(MetricId.entries.toSet(), used)
    }
}
