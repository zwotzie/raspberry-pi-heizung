package de.zwotzie.heizung.ui

import de.zwotzie.heizung.data.ChartApi
import de.zwotzie.heizung.data.ChartApiException
import de.zwotzie.heizung.data.ChartRow
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.Period
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.time.LocalDate

class DashboardViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private class FakeApi(
        var rows: List<ChartRow> = emptyList(),
        var error: Throwable? = null,
    ) : ChartApi {
        var calls = 0

        override suspend fun fetch(date: LocalDate, period: Period): List<ChartRow> {
            calls++
            error?.let { throw it }
            return rows
        }
    }

    private fun vm(api: ChartApi, url: String? = "https://h.example") =
        DashboardViewModel(api) { url }

    private fun sampleRows(count: Int) = (0 until count).map {
        ChartRow(
            timestampSec = 1_700_000_000 + it * 60L,
            values = MetricId.entries.associateWith { 20.0 + it },
        )
    }

    @Test
    fun `startet auf heute tag und puffer`() = runTest {
        val api = FakeApi(rows = sampleRows(3))
        val model = vm(api)
        advanceUntilIdle()

        assertEquals(0, model.state.value.tabIndex)
        assertEquals(Period.DAY, model.state.value.period)
        assertEquals(LocalDate.now(), model.state.value.date)
        assertEquals(3, model.state.value.rows.size)
        assertNull(model.state.value.error)
        assertFalse(model.state.value.loading)
    }

    @Test
    fun `ohne server-adresse wird nicht geladen und es gibt einen hinweis`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api, url = null)
        advanceUntilIdle()

        assertEquals(0, api.calls)
        assertNotNull(model.state.value.error)
        assertNull(model.state.value.serverUrl)
    }

    @Test
    fun `zurueck blaettert um einen tag und laedt neu`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api)
        advanceUntilIdle()

        model.previous()
        advanceUntilIdle()

        assertEquals(LocalDate.now().minusDays(1), model.state.value.date)
        assertEquals(2, api.calls)
    }

    @Test
    fun `reiterwechsel laedt nicht neu`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api)
        advanceUntilIdle()

        model.selectTab(2)
        advanceUntilIdle()

        assertEquals(2, model.state.value.tabIndex)
        assertEquals(1, api.calls)
    }

    @Test
    fun `legende blendet eine serie aus und wieder ein`() = runTest {
        val model = vm(FakeApi(rows = sampleRows(1)))
        advanceUntilIdle()

        model.toggleSeries(MetricId.SPEICHER_1_KOPF)
        assertTrue(MetricId.SPEICHER_1_KOPF in model.state.value.hidden)

        model.toggleSeries(MetricId.SPEICHER_1_KOPF)
        assertFalse(MetricId.SPEICHER_1_KOPF in model.state.value.hidden)
    }

    @Test
    fun `fehler wird als text angezeigt und retry laedt erneut`() = runTest {
        val api = FakeApi(error = ChartApiException("kaputt"))
        val model = vm(api)
        advanceUntilIdle()

        assertNotNull(model.state.value.error)
        assertFalse(model.state.value.loading)

        api.error = null
        api.rows = sampleRows(2)
        model.retry()
        advanceUntilIdle()

        assertNull(model.state.value.error)
        assertEquals(2, model.state.value.rows.size)
    }

    @Test
    fun `leere antwort setzt fenster auf null`() = runTest {
        val model = vm(FakeApi(rows = emptyList()))
        advanceUntilIdle()

        assertNull(model.state.value.window)
        assertNull(model.state.value.error)
    }

    @Test
    fun `zeitraumwechsel laedt neu und leert die ausgeblendeten serien`() = runTest {
        val api = FakeApi(rows = sampleRows(2))
        val model = vm(api)
        advanceUntilIdle()
        model.toggleSeries(MetricId.RAUM_RASPT)

        model.setPeriod(Period.WEEK)
        advanceUntilIdle()

        assertEquals(Period.WEEK, model.state.value.period)
        assertEquals(2, api.calls)
        assertTrue(model.state.value.hidden.isEmpty())
    }

    @Test
    fun `zurueck im wochenmodus springt sieben tage`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api)
        advanceUntilIdle()
        model.setPeriod(Period.WEEK)
        advanceUntilIdle()

        model.previous()
        advanceUntilIdle()

        assertEquals(LocalDate.now().minusDays(7), model.state.value.date)
    }
}
