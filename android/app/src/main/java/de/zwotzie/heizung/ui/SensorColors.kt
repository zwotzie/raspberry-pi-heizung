package de.zwotzie.heizung.ui

import androidx.compose.ui.graphics.Color
import de.zwotzie.heizung.data.MetricId

/** Feste Farben je Sensor, damit App und Weboberfläche gleich aussehen. */
object SensorColors {
    private val speicher1 = Color(0xFFF472B6)
    private val speicher2 = Color(0xFF4EA1FF)
    private val speicher3 = Color(0xFF6EE7B7)
    private val speicher4 = Color(0xFFFACC15)
    private val speicher5 = Color(0xFFC084FC)
    private val aussen = Color(0xFF9CA3AF)
    private val raum = Color(0xFFFB923C)
    private val kessel = Color(0xFFF87171)
    private val solar = Color(0xFFFACC15)
    private val drehzahl = Color(0xFF6EE7B7)
    private val digital = Color(0xFF34D399)

    fun of(metric: MetricId): Color = when (metric) {
        MetricId.SPEICHER_1_KOPF -> speicher1
        MetricId.SPEICHER_2_KOPF -> speicher2
        MetricId.SPEICHER_3_KOPF -> speicher3
        MetricId.SPEICHER_4_MITTE -> speicher4
        MetricId.SPEICHER_5_BODEN -> speicher5
        MetricId.AUSSENTEMPERATUR -> aussen
        MetricId.RAUM_RASPT -> raum
        MetricId.KESSEL_RL,
        MetricId.KESSEL_BETRIEBSTEMPERATUR,
        -> kessel
        MetricId.KESSEL_LADEPUMPE_DREHZAHL,
        MetricId.HEIZUNG_PUMPE_DREHZAHL,
        MetricId.SOLAR_LADEPUMPE_DREHZAHL,
        -> drehzahl
        MetricId.SOLAR_STRAHLUNG,
        MetricId.SOLAR_VL,
        -> solar
        MetricId.SPEICHER_LADELEITUNG,
        MetricId.HEIZUNG_VL,
        MetricId.HEIZUNG_RL,
        -> speicher2
        else -> digital
    }
}
