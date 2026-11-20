package de.zwotzie.heizung.data

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.longOrNull

/**
 * Liest die Antwort von `GET /api/chart`.
 *
 * Format: `[unix_ts, *17 analog, *11 digital]`, fehlende Werte als `null`.
 * Die Spaltenreihenfolge entspricht [MetricId.entries].
 */
object ChartJson {
    fun parse(body: String): List<ChartRow> {
        val root = try {
            Json.parseToJsonElement(body)
        } catch (exc: Exception) {
            throw IllegalArgumentException("Antwort ist kein JSON", exc)
        }
        val array = root as? JsonArray
            ?: throw IllegalArgumentException("Antwort ist kein Array")

        return array.map { element ->
            val row = element as? JsonArray
                ?: throw IllegalArgumentException("Zeile ist kein Array")
            val timestamp = row.firstOrNull()?.let { number(it)?.toLong() }
                ?: throw IllegalArgumentException("Zeitstempel fehlt")

            ChartRow(
                timestampSec = timestamp,
                values = MetricId.entries
                    .mapIndexed { index, metric -> metric to number(row.getOrNull(index + 1)) }
                    .toMap(),
            )
        }
    }

    private fun number(element: kotlinx.serialization.json.JsonElement?): Double? {
        if (element == null || element is JsonNull) return null
        val primitive = element as? JsonPrimitive ?: return null
        return primitive.doubleOrNull ?: primitive.content.toLongOrNull()?.toDouble()
    }
}
