package de.zwotzie.heizung.ui

import de.zwotzie.heizung.data.ServerUrl

/** Prüft die Eingabe im Einstellungsbildschirm. */
object SettingsValidation {
    /** `null`, wenn die Adresse brauchbar ist, sonst der Hinweistext. */
    fun messageFor(raw: String): String? = when {
        raw.isBlank() -> "Bitte eine Adresse eingeben"
        ServerUrl.normalize(raw) == null -> "Die Adresse muss mit https:// oder http:// beginnen"
        else -> null
    }
}
