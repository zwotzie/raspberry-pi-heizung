package de.zwotzie.heizung.ui

import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class SettingsValidationTest {
    @Test
    fun `leer ist ein fehler`() {
        assertNotNull(SettingsValidation.messageFor(""))
    }

    @Test
    fun `ohne https oder http ist ein fehler`() {
        assertNotNull(SettingsValidation.messageFor("heizung.example"))
    }

    @Test
    fun `gueltige adresse ergibt keine meldung`() {
        assertNull(SettingsValidation.messageFor("https://heizung.example/"))
    }

    @Test
    fun `nur schema ist ein fehler`() {
        assertNotNull(SettingsValidation.messageFor("https://"))
    }
}
