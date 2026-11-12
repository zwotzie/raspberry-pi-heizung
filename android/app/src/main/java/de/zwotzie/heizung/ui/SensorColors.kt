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

    // Digitalbänder: eine Farbe je Aufgabe, damit sich die Bänder eines Reiters
    // unterscheiden lassen. Töne stammen aus der Palette oben, damit App und
    // Weboberfläche zusammenpassen.
    private val digitalPumpe = Color(0xFF4EA1FF)
    private val digitalFreigabe = Color(0xFFC084FC)
    private val digitalMischerAuf = Color(0xFF34D399)
    private val digitalMischerZu = Color(0xFFFB923C)
    private val digitalAnlageAn = Color(0xFFF87171)
    private val digitalSolarPumpe = Color(0xFFFACC15)

    fun of(metric: MetricId): Color = when (metric) {
        MetricId.SPEICHER_1_KOPF -> speicher1
        MetricId.SPEICHER_2_KOPF -> speicher2
        MetricId.SPEICHER_3_KOPF -> speicher3
        MetricId.SPEICHER_4_MITTE -> speicher4
        MetricId.SPEICHER_5_BODEN -> speicher5
        MetricId.AUSSENTEMPERATUR -> aussen
        MetricId.RAUM_RASPT -> raum
        MetricId.KESSEL_RL -> kessel
        MetricId.KESSEL_BETRIEBSTEMPERATUR -> Color(0xFFFCA5A5)
        MetricId.KESSEL_LADEPUMPE_DREHZAHL,
        MetricId.HEIZUNG_PUMPE_DREHZAHL,
        MetricId.SOLAR_LADEPUMPE_DREHZAHL,
        -> drehzahl
        MetricId.SOLAR_STRAHLUNG -> solar
        MetricId.SOLAR_VL -> Color(0xFFF59E0B)
        MetricId.SPEICHER_LADELEITUNG -> Color(0xFFA3E635)
        MetricId.HEIZUNG_VL -> speicher2
        MetricId.HEIZUNG_RL -> speicher1
        MetricId.D_HEIZUNG_PUMPE,
        MetricId.D_KESSEL_LADEPUMPE,
        MetricId.D_SOLAR_KREISPUMPE,
        -> digitalPumpe
        MetricId.D_HEIZUNG_MISCHER_AUF,
        MetricId.D_KESSEL_MISCHER_AUF,
        -> digitalMischerAuf
        MetricId.D_HEIZUNG_MISCHER_ZU,
        MetricId.D_KESSEL_MISCHER_ZU,
        -> digitalMischerZu
        MetricId.D_KESSEL_FREIGABE,
        MetricId.D_SOLAR_FREIGABEPUMPE,
        -> digitalFreigabe
        MetricId.D_SOLAR_LADEPUMPE -> digitalSolarPumpe
        MetricId.HEIZUNG_AN -> digitalAnlageAn
        else -> digitalMischerAuf
    }

    /** Fläche eines eingeschalteten Digitalbands. */
    fun bandFill(metric: MetricId): Color = of(metric).copy(alpha = 0.32f)

    /** Schwache Fläche, die auch den Aus-Zustand in der Bandfarbe zeigt. */
    fun bandTint(metric: MetricId): Color = of(metric).copy(alpha = 0.12f)
}
