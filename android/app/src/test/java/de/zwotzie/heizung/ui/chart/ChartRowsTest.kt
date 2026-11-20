package de.zwotzie.heizung.ui.chart

import de.zwotzie.heizung.data.ChartRow
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.ViewWindow
import org.junit.Assert.assertEquals
import org.junit.Test

class ChartRowsTest {
    private fun row(ts: Long) = ChartRow(ts, MetricId.entries.associateWith { 20.0 })

    @Test
    fun `fenster ueber alles liefert alle zeilen`() {
        val rows = (0 until 5).map { row(1_000L + it * 60) }
        assertEquals(rows, ChartRows.visible(rows, ViewWindow(1_000, 1_300)))
    }

    @Test
    fun `fenster mit einer zeile liefert genau eine statt aller`() {
        val rows = (0 until 5).map { row(1_000L + it * 60) }
        val visible = ChartRows.visible(rows, ViewWindow(1_060, 1_090))
        assertEquals(1, visible.size)
        assertEquals(1_060L, visible.first().timestampSec)
    }

    @Test
    fun `fenster ohne zeilen liefert leer`() {
        val rows = (0 until 5).map { row(1_000L + it * 60) }
        assertEquals(emptyList<ChartRow>(), ChartRows.visible(rows, ViewWindow(5_000, 5_600)))
    }

    @Test
    fun `ohne zeilen bleibt es leer`() {
        assertEquals(emptyList<ChartRow>(), ChartRows.visible(emptyList(), ViewWindow(0, 60)))
    }
}
