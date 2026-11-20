package de.zwotzie.heizung.data

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate

class ApiUrlTest {
    private val date = LocalDate.of(2026, 11, 11)

    @Test
    fun `ohne schraegstrich am ende`() {
        assertEquals(
            "https://h.example/api/chart?date=2026-11-11&period=day",
            ApiUrl.chart("https://h.example", date, Period.DAY),
        )
    }

    @Test
    fun `mit schraegstrich am ende`() {
        assertEquals(
            "https://h.example/api/chart?date=2026-11-11&period=week",
            ApiUrl.chart("https://h.example/", date, Period.WEEK),
        )
    }

    @Test
    fun `mit pfad in der basis`() {
        assertEquals(
            "https://h.example/heizung/api/chart?date=2026-11-11&period=day",
            ApiUrl.chart("https://h.example/heizung/", date, Period.DAY),
        )
    }
}
