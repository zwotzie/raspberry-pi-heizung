package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ServerUrlTest {
    @Test
    fun `leer ergibt null`() {
        assertNull(ServerUrl.normalize("  "))
    }

    @Test
    fun `ohne schema ergibt null`() {
        assertNull(ServerUrl.normalize("heizung.example"))
    }

    @Test
    fun `schraegstrich und leerzeichen werden entfernt`() {
        assertEquals("https://h.example", ServerUrl.normalize(" https://h.example/ "))
    }

    @Test
    fun `http bleibt erlaubt`() {
        assertEquals("http://192.168.1.9:8000", ServerUrl.normalize("http://192.168.1.9:8000"))
    }

    @Test
    fun `pfad bleibt erhalten`() {
        assertEquals("https://h.example/heizung", ServerUrl.normalize("https://h.example/heizung/"))
    }

    @Test
    fun `nur schema ergibt null`() {
        assertNull(ServerUrl.normalize("https://"))
    }
}
