package de.zwotzie.heizung.ui.chart

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ChartScaleTest {
    @Test
    fun `leere werte ergeben einen sinnvollen bereich`() {
        val range = ChartScale.range(emptyList(), minSpan = 5.0)
        assertTrue(range.endInclusive > range.start)
    }

    @Test
    fun `konstante linie bekommt mindestspanne`() {
        val range = ChartScale.range(listOf(40.0, 40.0, 40.0), minSpan = 5.0)
        assertEquals(5.0, range.endInclusive - range.start, 0.001)
        assertTrue(range.start < 40.0 && range.endInclusive > 40.0)
    }

    @Test
    fun `nulls werden ignoriert`() {
        val range = ChartScale.range(listOf(null, 10.0, null, 30.0), minSpan = 1.0)
        assertTrue(range.start <= 10.0 && range.endInclusive >= 30.0)
    }

    @Test
    fun `ausreisser sprengen den bereich nicht unbegrenzt`() {
        val range = ChartScale.range(listOf(1.0, 2.0, 3.0, 1000.0), minSpan = 1.0)
        assertTrue(range.endInclusive <= 1200.0)
        assertEquals(1.0, range.start, 0.001)
    }

    @Test
    fun `nur unendliche werte ergeben den standardbereich`() {
        val range = ChartScale.range(listOf(Double.NaN, Double.POSITIVE_INFINITY), minSpan = 2.0)
        assertEquals(2.0, range.endInclusive - range.start, 0.001)
    }

    @Test
    fun `y wert liegt zwischen oben und unten`() {
        val range = 0.0..100.0
        assertEquals(0f, ChartScale.yOf(100.0, range, top = 0f, bottom = 200f))
        assertEquals(200f, ChartScale.yOf(0.0, range, top = 0f, bottom = 200f))
        assertEquals(100f, ChartScale.yOf(50.0, range, top = 0f, bottom = 200f))
    }

    @Test
    fun `werte ausserhalb der skala werden geklemmt`() {
        val range = 0.0..100.0
        assertEquals(0f, ChartScale.yOf(150.0, range, top = 0f, bottom = 200f))
        assertEquals(200f, ChartScale.yOf(-50.0, range, top = 0f, bottom = 200f))
    }
}
