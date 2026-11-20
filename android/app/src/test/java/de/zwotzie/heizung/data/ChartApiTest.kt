package de.zwotzie.heizung.data

import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class ChartApiTest {
    private val server = MockWebServer()

    private fun api(): HttpChartApi =
        HttpChartApi(baseUrl = { server.url("/").toString().trimEnd('/') })

    @Test
    fun `holt und parst die antwort`() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """[[1731250800,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28]]""",
            ),
        )

        val rows = api().fetch(LocalDate.of(2026, 11, 11), Period.DAY)

        assertEquals(1, rows.size)
        assertEquals(1.0, rows[0].values[MetricId.KESSEL_RL])
        assertEquals("/api/chart?date=2026-11-11&period=day", server.takeRequest().path)
    }

    @Test
    fun `http-fehler wird zur exception mit status`() = runTest {
        server.enqueue(MockResponse().setResponseCode(502))

        val error = runCatching { api().fetch(LocalDate.of(2026, 11, 11), Period.DAY) }.exceptionOrNull()

        assertTrue(error is ChartApiException)
        assertEquals(502, (error as ChartApiException).status)
    }

    @Test
    fun `unerreichbarer server wird zur exception ohne status`() = runTest {
        server.shutdown()

        val error = runCatching { api().fetch(LocalDate.of(2026, 11, 11), Period.DAY) }.exceptionOrNull()

        assertTrue(error is ChartApiException)
        assertEquals(null, (error as ChartApiException).status)
    }
}
