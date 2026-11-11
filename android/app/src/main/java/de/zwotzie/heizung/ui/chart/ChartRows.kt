package de.zwotzie.heizung.ui.chart

import de.zwotzie.heizung.data.ChartRow
import de.zwotzie.heizung.data.ViewWindow

/** Wählt die Zeilen, die im sichtbaren Zeitausschnitt liegen. */
object ChartRows {
    fun visible(rows: List<ChartRow>, window: ViewWindow): List<ChartRow> =
        rows.filter { it.timestampSec in window.startSec..window.endSec }
}
