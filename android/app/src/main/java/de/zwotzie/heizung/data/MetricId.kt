package de.zwotzie.heizung.data

/**
 * Sensor-Metriken in der Spaltenreihenfolge der API.
 *
 * Reihenfolge und Namen müssen zu `src/heizung/metrics.py` passen:
 * erst 17 analoge Werte, dann 11 digitale.
 */
enum class MetricId(val apiName: String) {
    KESSEL_RL("kessel_rl"),
    KESSEL_LADEPUMPE_DREHZAHL("kessel_ladepumpe_drehzahl"),
    KESSEL_BETRIEBSTEMPERATUR("kessel_betriebstemperatur"),
    SPEICHER_LADELEITUNG("speicher_ladeleitung"),
    AUSSENTEMPERATUR("aussentemperatur"),
    RAUM_RASPT("raum_rasp"),
    SPEICHER_1_KOPF("speicher_1_kopf"),
    SPEICHER_2_KOPF("speicher_2_kopf"),
    SPEICHER_3_KOPF("speicher_3_kopf"),
    SPEICHER_4_MITTE("speicher_4_mitte"),
    SPEICHER_5_BODEN("speicher_5_boden"),
    HEIZUNG_VL("heizung_vl"),
    HEIZUNG_RL("heizung_rl"),
    HEIZUNG_PUMPE_DREHZAHL("heizung_pumpe_drehzahl"),
    SOLAR_STRAHLUNG("solar_strahlung"),
    SOLAR_VL("solar_vl"),
    SOLAR_LADEPUMPE_DREHZAHL("solar_ladepumpe_drehzahl"),
    D_HEIZUNG_PUMPE("d_heizung_pumpe"),
    D_KESSEL_LADEPUMPE("d_kessel_ladepumpe"),
    D_KESSEL_FREIGABE("d_kessel_freigabe"),
    D_HEIZUNG_MISCHER_AUF("d_heizung_mischer_auf"),
    D_HEIZUNG_MISCHER_ZU("d_heizung_mischer_zu"),
    D_KESSEL_MISCHER_AUF("d_kessel_mischer_auf"),
    D_KESSEL_MISCHER_ZU("d_kessel_mischer_zu"),
    D_SOLAR_KREISPUMPE("d_solar_kreispumpe"),
    D_SOLAR_LADEPUMPE("d_solar_ladepumpe"),
    D_SOLAR_FREIGABEPUMPE("d_solar_freigabepumpe"),
    HEIZUNG_AN("heizung_an"),
}
