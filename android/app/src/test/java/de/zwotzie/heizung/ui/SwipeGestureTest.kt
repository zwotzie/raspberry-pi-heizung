package de.zwotzie.heizung.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class SwipeGestureTest {
    private val width = 900f

    @Test
    fun `linkswisch ueber ein drittel wechselt zum naechsten tab`() {
        assertEquals(1, SwipeGesture.direction(-300f, width, elapsedMs = 500))
    }

    @Test
    fun `rechtswisch ueber ein drittel wechselt zum vorherigen tab`() {
        assertEquals(-1, SwipeGesture.direction(300f, width, elapsedMs = 500))
    }

    @Test
    fun `kurzer zuegiger wisch reicht ebenfalls`() {
        assertEquals(1, SwipeGesture.direction(-150f, width, elapsedMs = 200))
        assertEquals(-1, SwipeGesture.direction(150f, width, elapsedMs = 120))
    }

    @Test
    fun `kurzer langsamer wisch aendert nichts`() {
        assertEquals(0, SwipeGesture.direction(-150f, width, elapsedMs = 400))
    }

    @Test
    fun `bewegung unter einem sechstel aendert nichts`() {
        assertEquals(0, SwipeGesture.direction(-149f, width, elapsedMs = 100))
    }

    @Test
    fun `knapp unter einem drittel in langsamer zeit aendert nichts`() {
        assertEquals(0, SwipeGesture.direction(-299f, width, elapsedMs = 800))
    }

    @Test
    fun `ohne breite gibt es keine richtung`() {
        assertEquals(0, SwipeGesture.direction(-300f, 0f, elapsedMs = 100))
    }

    @Test
    fun `tab umlauf am ende zum anfang`() {
        assertEquals(0, cycleTab(index = 3, delta = 1, count = 4))
    }

    @Test
    fun `tab umlauf am anfang zum ende`() {
        assertEquals(3, cycleTab(index = 0, delta = -1, count = 4))
    }

    @Test
    fun `tab schritt in der mitte bleibt in der liste`() {
        assertEquals(2, cycleTab(index = 1, delta = 1, count = 4))
    }
}
