package de.zwotzie.heizung.ui

import de.zwotzie.heizung.data.Catalog
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.Unit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SensorColorsTest {
    @Test
    fun `kurven eines reiters sind farblich unterscheidbar`() {
        Catalog.tabs.forEach { tab ->
            val metrics = tab.temperatures + tab.rows
            val colors = metrics.map { SensorColors.of(it) }
            assertEquals(
                "Reiter ${tab.title} hat doppelte Farben",
                metrics.size,
                colors.toSet().size,
            )
        }
    }

    @Test
    fun `einheiten ausser celsius stehen im legendentext`() {
        val entries = LegendEntries.of(Catalog.tabs[1])
        val strahlung = entries.first { it.metric == MetricId.SOLAR_STRAHLUNG }
        val pumpe = entries.first { it.metric == MetricId.SOLAR_LADEPUMPE_DREHZAHL }

        assertTrue(strahlung.label.contains(Unit.WATT_PER_M2.label))
        assertTrue(pumpe.label.contains(Unit.PERCENT.label))
    }

    @Test
    fun `celsius steht nicht im legendentext`() {
        val eintrag = LegendEntries.of(Catalog.tabs[0]).first { it.metric == MetricId.SPEICHER_1_KOPF }
        assertTrue(!eintrag.label.contains(Unit.CELSIUS.label))
    }
}
