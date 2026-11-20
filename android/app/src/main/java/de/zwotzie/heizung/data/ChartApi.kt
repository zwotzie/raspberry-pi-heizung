package de.zwotzie.heizung.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.time.LocalDate
import java.util.concurrent.TimeUnit

/** Zeitraum der Abfrage; entspricht dem `period`-Parameter der API. */
enum class Period { DAY, WEEK }

/** Zugriff auf die Chart-Daten der Heizungs-API. */
interface ChartApi {
    suspend fun fetch(date: LocalDate, period: Period): List<ChartRow>
}

/** Fehler beim Abruf; [status] ist gesetzt, wenn der Server geantwortet hat. */
class ChartApiException(message: String, val status: Int? = null) : Exception(message)

/** Baut die Abfrage-URL; ein Pfad in der Basis bleibt erhalten. */
object ApiUrl {
    fun chart(baseUrl: String, date: LocalDate, period: Period): String =
        "${baseUrl.trimEnd('/')}/api/chart?date=$date&period=${period.name.lowercase()}"
}

/** Holt die Chart-Daten per HTTP und liest sie mit [ChartJson]. */
class HttpChartApi(
    private val baseUrl: () -> String,
    private val client: OkHttpClient = defaultClient(),
) : ChartApi {

    override suspend fun fetch(date: LocalDate, period: Period): List<ChartRow> =
        withContext(Dispatchers.IO) {
            val request = Request.Builder()
                .url(ApiUrl.chart(baseUrl(), date, period))
                .get()
                .build()

            val response = try {
                client.newCall(request).execute()
            } catch (exc: IOException) {
                throw ChartApiException("Server nicht erreichbar: ${exc.message}")
            }

            response.use { answer ->
                if (!answer.isSuccessful) {
                    throw ChartApiException("Server antwortet mit ${answer.code}", answer.code)
                }
                val body = answer.body?.string()
                    ?: throw ChartApiException("Leere Antwort")
                if (body.length > MAX_BODY_CHARS) {
                    throw ChartApiException("Antwort ist zu groß")
                }
                try {
                    ChartJson.parse(body)
                } catch (exc: IllegalArgumentException) {
                    throw ChartApiException("Antwort nicht lesbar: ${exc.message}")
                }
            }
        }

    companion object {
        private const val MAX_BODY_CHARS = 8 * 1024 * 1024

        private fun defaultClient(): OkHttpClient = OkHttpClient.Builder()
            .callTimeout(15, TimeUnit.SECONDS)
            .build()
    }
}
