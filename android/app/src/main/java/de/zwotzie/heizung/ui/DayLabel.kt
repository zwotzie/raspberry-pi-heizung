package de.zwotzie.heizung.ui

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Beschriftung des angezeigten Tages; „Heute" nur, wenn es wirklich heute ist. */
object DayLabel {
    private val format = DateTimeFormatter.ofPattern("EEE, d. MMM", Locale.GERMAN)

    fun of(date: LocalDate, today: LocalDate): String =
        if (date == today) "Heute" else date.format(format)
}
