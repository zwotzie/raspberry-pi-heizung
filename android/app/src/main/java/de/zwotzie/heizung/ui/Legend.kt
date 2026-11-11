package de.zwotzie.heizung.ui

import de.zwotzie.heizung.data.Catalog
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.TabSpec
import de.zwotzie.heizung.data.Unit
import androidx.compose.ui.graphics.Color

/** Ein Eintrag der Legende: Farbe, Name und die dahinterliegende Serie. */
data class LegendEntry(
    val metric: MetricId,
    val label: String,
    val color: Color,
)

/** Baut die Legende eines Reiters in Zeichenreihenfolge. */
object LegendEntries {
    fun of(spec: TabSpec): List<LegendEntry> =
        (spec.temperatures + spec.rows + spec.digital).map { metric ->
            val series = Catalog.spec(metric)
            LegendEntry(
                metric = metric,
                label = if (series.unit == Unit.CELSIUS) {
                    series.label
                } else {
                    "${series.label} · ${series.unit.label}"
                },
                color = SensorColors.of(metric),
            )
        }
}
