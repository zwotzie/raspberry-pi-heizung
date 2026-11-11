package de.zwotzie.heizung.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/** Prüft und vereinheitlicht die vom Nutzer eingegebene Server-Adresse. */
object ServerUrl {
    /** `null`, wenn leer oder ohne `http(s)://`; sonst ohne Schrägstriche am Ende. */
    fun normalize(raw: String): String? {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) return null

        val lower = trimmed.lowercase()
        if (!lower.startsWith("http://") && !lower.startsWith("https://")) return null

        val scheme = trimmed.substringBefore("://")
        val rest = trimmed.substringAfter("://").trimEnd('/')
        return if (rest.isEmpty()) null else "$scheme://$rest"
    }
}

private val Context.dataStore by preferencesDataStore(name = "heizung")

/** Merkt sich die Server-Adresse über App-Starts hinweg. */
class SettingsStore(private val context: Context) {
    val serverUrl: Flow<String?> = context.dataStore.data.map { it[KEY] }

    suspend fun save(raw: String) {
        val normalized = ServerUrl.normalize(raw) ?: return
        context.dataStore.edit { it[KEY] = normalized }
    }

    private companion object {
        val KEY = stringPreferencesKey("server_url")
    }
}
