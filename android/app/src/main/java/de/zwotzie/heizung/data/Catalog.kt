package de.zwotzie.heizung.data

/** Einheit einer Serie; bestimmt Achsenbeschriftung und in welcher Zeile sie landet. */
enum class Unit(val label: String) {
    CELSIUS("°C"),
    PERCENT("%"),
    WATT_PER_M2("W/m²"),
}

/** Anzeigedaten einer einzelnen Metrik. */
data class SeriesSpec(
    val metric: MetricId,
    val label: String,
    val unit: Unit,
)

/**
 * Ein Reiter: welche Kurven im großen Feld stehen, welche eine eigene schmale
 * Zeile bekommen und welche als Digitalband laufen.
 */
data class TabSpec(
    val title: String,
    val temperatures: List<MetricId>,
    val rows: List<MetricId>,
    val digital: List<MetricId>,
)

/** Aufbau der vier Reiter, identisch zur Web-Oberfläche (`uvr-charts.js`). */
object Catalog {
    private val specs: Map<MetricId, SeriesSpec> = listOf(
        SeriesSpec(MetricId.KESSEL_RL, "RL Kessel", Unit.CELSIUS),
        SeriesSpec(MetricId.KESSEL_LADEPUMPE_DREHZAHL, "Kesselpumpe", Unit.PERCENT),
        SeriesSpec(MetricId.KESSEL_BETRIEBSTEMPERATUR, "Kesseltemperatur", Unit.CELSIUS),
        SeriesSpec(MetricId.SPEICHER_LADELEITUNG, "Ladeleitung", Unit.CELSIUS),
        SeriesSpec(MetricId.AUSSENTEMPERATUR, "Außen", Unit.CELSIUS),
        SeriesSpec(MetricId.RAUM_RASPT, "Raum", Unit.CELSIUS),
        SeriesSpec(MetricId.SPEICHER_1_KOPF, "1 Kopf", Unit.CELSIUS),
        SeriesSpec(MetricId.SPEICHER_2_KOPF, "2 Oben", Unit.CELSIUS),
        SeriesSpec(MetricId.SPEICHER_3_KOPF, "3 Unten", Unit.CELSIUS),
        SeriesSpec(MetricId.SPEICHER_4_MITTE, "4 Mitte", Unit.CELSIUS),
        SeriesSpec(MetricId.SPEICHER_5_BODEN, "5 Boden", Unit.CELSIUS),
        SeriesSpec(MetricId.HEIZUNG_VL, "VL Heizung", Unit.CELSIUS),
        SeriesSpec(MetricId.HEIZUNG_RL, "RL Heizung", Unit.CELSIUS),
        SeriesSpec(MetricId.HEIZUNG_PUMPE_DREHZAHL, "Heizungspumpe", Unit.PERCENT),
        SeriesSpec(MetricId.SOLAR_STRAHLUNG, "Solarstrahlung", Unit.WATT_PER_M2),
        SeriesSpec(MetricId.SOLAR_VL, "VL Solar", Unit.CELSIUS),
        SeriesSpec(MetricId.SOLAR_LADEPUMPE_DREHZAHL, "Solarpumpe", Unit.PERCENT),
        SeriesSpec(MetricId.D_HEIZUNG_PUMPE, "Heizung: Pumpe", Unit.PERCENT),
        SeriesSpec(MetricId.D_KESSEL_LADEPUMPE, "Kessel: Ladepumpe", Unit.PERCENT),
        SeriesSpec(MetricId.D_KESSEL_FREIGABE, "Kessel: Freigabe", Unit.PERCENT),
        SeriesSpec(MetricId.D_HEIZUNG_MISCHER_AUF, "Hz Mischer auf", Unit.PERCENT),
        SeriesSpec(MetricId.D_HEIZUNG_MISCHER_ZU, "Hz Mischer zu", Unit.PERCENT),
        SeriesSpec(MetricId.D_KESSEL_MISCHER_AUF, "Kessel Mischer auf", Unit.PERCENT),
        SeriesSpec(MetricId.D_KESSEL_MISCHER_ZU, "Kessel Mischer zu", Unit.PERCENT),
        SeriesSpec(MetricId.D_SOLAR_KREISPUMPE, "Solarkreispumpe", Unit.PERCENT),
        SeriesSpec(MetricId.D_SOLAR_LADEPUMPE, "Solar: Ladepumpe", Unit.PERCENT),
        SeriesSpec(MetricId.D_SOLAR_FREIGABEPUMPE, "Solar: Freigabe", Unit.PERCENT),
        SeriesSpec(MetricId.HEIZUNG_AN, "Heizung An", Unit.PERCENT),
    ).associateBy { it.metric }

    val tabs: List<TabSpec> = listOf(
        TabSpec(
            title = "Puffer",
            temperatures = listOf(
                MetricId.AUSSENTEMPERATUR,
                MetricId.RAUM_RASPT,
                MetricId.SPEICHER_1_KOPF,
                MetricId.SPEICHER_2_KOPF,
                MetricId.SPEICHER_3_KOPF,
                MetricId.SPEICHER_4_MITTE,
                MetricId.SPEICHER_5_BODEN,
            ),
            rows = emptyList(),
            digital = emptyList(),
        ),
        TabSpec(
            title = "Solar",
            temperatures = listOf(MetricId.AUSSENTEMPERATUR, MetricId.SOLAR_VL),
            rows = listOf(MetricId.SOLAR_STRAHLUNG, MetricId.SOLAR_LADEPUMPE_DREHZAHL),
            digital = listOf(
                MetricId.D_SOLAR_KREISPUMPE,
                MetricId.D_SOLAR_LADEPUMPE,
                MetricId.D_SOLAR_FREIGABEPUMPE,
            ),
        ),
        TabSpec(
            title = "Heizung",
            temperatures = listOf(MetricId.HEIZUNG_VL, MetricId.HEIZUNG_RL),
            rows = listOf(MetricId.HEIZUNG_PUMPE_DREHZAHL),
            digital = listOf(
                MetricId.D_HEIZUNG_PUMPE,
                MetricId.D_HEIZUNG_MISCHER_AUF,
                MetricId.D_HEIZUNG_MISCHER_ZU,
            ),
        ),
        TabSpec(
            title = "Erzeuger",
            temperatures = listOf(
                MetricId.KESSEL_RL,
                MetricId.KESSEL_BETRIEBSTEMPERATUR,
                MetricId.SPEICHER_LADELEITUNG,
            ),
            rows = listOf(MetricId.KESSEL_LADEPUMPE_DREHZAHL),
            digital = listOf(
                MetricId.HEIZUNG_AN,
                MetricId.D_KESSEL_LADEPUMPE,
                MetricId.D_KESSEL_FREIGABE,
                MetricId.D_KESSEL_MISCHER_AUF,
                MetricId.D_KESSEL_MISCHER_ZU,
            ),
        ),
    )

    fun spec(metric: MetricId): SeriesSpec =
        specs.getValue(metric)
}
