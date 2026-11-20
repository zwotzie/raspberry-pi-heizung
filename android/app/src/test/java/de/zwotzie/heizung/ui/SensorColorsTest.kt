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
    fun `digitale baender eines reiters sind farblich unterscheidbar`() {
        Catalog.tabs.forEach { tab ->
            val colors = tab.digital.map { SensorColors.of(it) }
            assertEquals(
                "Reiter ${tab.title} hat doppelte Digitalfarben",
                colors.size,
                colors.toSet().size,
            )
        }
    }

    @Test
    fun `digitalband bleibt im aus zustand in seiner farbe sichtbar`() {
        val metric = MetricId.D_KESSEL_FREIGABE
        val base = SensorColors.of(metric)
        val fill = SensorColors.bandFill(metric)
        val tint = SensorColors.bandTint(metric)

        assertEquals(base.red.toDouble(), tint.red.toDouble(), 0.0001)
        assertEquals(base.green.toDouble(), tint.green.toDouble(), 0.0001)
        assertEquals(base.blue.toDouble(), tint.blue.toDouble(), 0.0001)
        assertTrue("Aus-Zustand muss sichtbar bleiben", tint.alpha > 0f)
        assertTrue("Aus-Zustand ist schwächer als die An-Fläche", tint.alpha < fill.alpha)
        assertTrue("An-Fläche bleibt durchscheinend", fill.alpha < base.alpha)
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
