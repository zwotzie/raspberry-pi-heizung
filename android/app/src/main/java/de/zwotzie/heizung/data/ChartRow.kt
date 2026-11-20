package de.zwotzie.heizung.data

/** Eine Messzeile der API: Zeitstempel in Sekunden und die Werte je Metrik. */
data class ChartRow(
    val timestampSec: Long,
    val values: Map<MetricId, Double?>,
)
