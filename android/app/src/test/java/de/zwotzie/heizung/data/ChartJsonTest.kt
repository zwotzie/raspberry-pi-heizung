package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ChartJsonTest {
    private fun fixture() = javaClass.getResource("/chart_day.json")!!.readText()

    @Test
    fun `spalten landen bei den richtigen metriken`() {
        val rows = ChartJson.parse(fixture())
        assertEquals(2, rows.size)
        assertEquals(1.0, rows[0].values[MetricId.KESSEL_RL])
        assertEquals(28.0, rows[0].values[MetricId.HEIZUNG_AN])
        assertEquals(1731250800L, rows[0].timestampSec)
    }

    @Test
    fun `null bleibt null und wird nicht zu null-komma-null`() {
        val rows = ChartJson.parse(fixture())
        assertNull(rows[1].values[MetricId.KESSEL_LADEPUMPE_DREHZAHL])
        assertNull(rows[1].values[MetricId.KESSEL_BETRIEBSTEMPERATUR])
    }

    @Test
    fun `leere antwort ergibt leere liste`() {
        assertEquals(emptyList<ChartRow>(), ChartJson.parse("[]"))
    }

    @Test
    fun `zeile mit nur zeitstempel wird nicht verworfen`() {
        val rows = ChartJson.parse("""[[1731250800]]""")
        assertEquals(1, rows.size)
        assertNull(rows[0].values[MetricId.KESSEL_RL])
    }

    @Test(expected = IllegalArgumentException::class)
    fun `kaputtes json wirft`() {
        ChartJson.parse("nicht json")
    }

    @Test(expected = IllegalArgumentException::class)
    fun `antwort ohne array wirft`() {
        ChartJson.parse("""{"error":"kaputt"}""")
    }
}
