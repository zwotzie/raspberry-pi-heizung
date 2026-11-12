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
    fun `gitterbereich wird auf zehnerstellen aufgeweitet`() {
        val range = ChartScale.gridRange(35.0..48.0, step = 10.0)
        assertEquals(30.0, range.start, 0.001)
        assertEquals(50.0, range.endInclusive, 0.001)
    }

    @Test
    fun `gitterbereich bleibt bei passenden grenzen unveraendert`() {
        val range = ChartScale.gridRange(30.0..50.0, step = 10.0)
        assertEquals(30.0, range.start, 0.001)
        assertEquals(50.0, range.endInclusive, 0.001)
    }

    @Test
    fun `gitterlinien liegen auf zehnerstellen`() {
        val range = ChartScale.gridRange(35.0..48.0, step = 10.0)
        assertEquals(listOf(30.0, 40.0, 50.0), ChartScale.gridValues(range, step = 10.0))
    }

    @Test
    fun `gitterlinien funktionieren auch unter null grad`() {
        val range = ChartScale.gridRange(-3.0..7.0, step = 10.0)
        assertEquals(-10.0, range.start, 0.001)
        assertEquals(10.0, range.endInclusive, 0.001)
        assertEquals(listOf(-10.0, 0.0, 10.0), ChartScale.gridValues(range, step = 10.0))
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
