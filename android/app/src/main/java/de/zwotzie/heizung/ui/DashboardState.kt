package de.zwotzie.heizung.ui

import de.zwotzie.heizung.data.ChartRow
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.Period
import de.zwotzie.heizung.data.ViewWindow
import java.time.LocalDate

/** Alles, was der Hauptbildschirm zum Zeichnen braucht. */
data class DashboardState(
    val serverUrl: String? = null,
    val date: LocalDate = LocalDate.now(),
    /** True, solange die Ansicht dem heutigen Tag folgt (nicht bewusst geblättert). */
    val followToday: Boolean = true,
    val period: Period = Period.DAY,
    val tabIndex: Int = 0,
    val hidden: Set<MetricId> = emptySet(),
    val rows: List<ChartRow> = emptyList(),
    val window: ViewWindow? = null,
    val loading: Boolean = false,
    val error: String? = null,
)
