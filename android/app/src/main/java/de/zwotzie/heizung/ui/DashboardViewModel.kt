package de.zwotzie.heizung.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.zwotzie.heizung.data.ChartApi
import de.zwotzie.heizung.data.ChartApiException
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.Period
import de.zwotzie.heizung.data.TimeWindow
import de.zwotzie.heizung.data.ViewWindow
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate

/**
 * Zustand des Hauptbildschirms: gewählter Tag, Zeitraum, Reiter und die Daten.
 *
 * Die Server-Adresse kommt als Funktion herein, damit ein Wechsel in den
 * Einstellungen ohne Neustart ankommt.
 */
class DashboardViewModel(
    private val api: ChartApi,
    private val serverUrl: () -> String?,
    private val clock: () -> LocalDate = { LocalDate.now() },
) : ViewModel() {

    private val _state = MutableStateFlow(
        DashboardState(date = clock(), serverUrl = null, loading = true),
    )
    val state: StateFlow<DashboardState> = _state.asStateFlow()

    private var loadJob: Job? = null

    init {
        load()
    }

    fun load() {
        val url = serverUrl()?.takeIf { it.isNotBlank() }
        if (url == null) {
            loadJob?.cancel()
            _state.update {
                it.copy(
                    serverUrl = null,
                    loading = false,
                    rows = emptyList(),
                    window = null,
                    error = "Keine Server-Adresse hinterlegt",
                )
            }
            return
        }

        val now = clock()
        val date = if (_state.value.followToday) now else _state.value.date
        val period = _state.value.period
        _state.update { it.copy(date = date, serverUrl = url, loading = true, error = null) }

        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            try {
                val rows = api.fetch(date, period)
                _state.update {
                    it.copy(loading = false, rows = rows, window = TimeWindow.of(rows), error = null)
                }
            } catch (exc: ChartApiException) {
                _state.update {
                    it.copy(loading = false, rows = emptyList(), window = null, error = message(exc))
                }
            } catch (exc: Exception) {
                _state.update {
                    it.copy(
                        loading = false,
                        rows = emptyList(),
                        window = null,
                        error = "Unerwarteter Fehler: ${exc.message}",
                    )
                }
            }
        }
    }

    fun retry() = load()

    /** Wird nach dem Speichern einer neuen Server-Adresse aufgerufen. */
    fun onServerUrlChanged() = load()

    fun setPeriod(period: Period) {
        if (_state.value.period == period) return
        _state.update { it.copy(period = period, hidden = emptySet()) }
        load()
    }

    fun previous() = moveBy(stepDays().let { -it })

    fun next() = moveBy(stepDays())

    fun today() {
        val now = clock()
        _state.update {
            if (it.date == now) {
                it.copy(followToday = true)
            } else {
                it.copy(date = now, followToday = true, hidden = emptySet())
            }
        }
        load()
    }

    fun selectTab(index: Int) {
        _state.update { it.copy(tabIndex = index) }
    }

    fun toggleSeries(metric: MetricId) {
        _state.update {
            val hidden = if (metric in it.hidden) it.hidden - metric else it.hidden + metric
            it.copy(hidden = hidden)
        }
    }

    fun pan(deltaSec: Long) {
        val state = _state.value
        val window = state.window ?: return
        val bounds = TimeWindow.of(state.rows) ?: return
        _state.update { it.copy(window = TimeWindow.pan(window, deltaSec, bounds)) }
    }

    fun zoom(factor: Double, anchorSec: Long) {
        val state = _state.value
        val window = state.window ?: return
        val bounds = TimeWindow.of(state.rows) ?: return
        _state.update { it.copy(window = TimeWindow.zoom(window, factor, anchorSec, bounds)) }
    }

    fun resetZoom() {
        val rows = _state.value.rows
        _state.update { it.copy(window = TimeWindow.of(rows)) }
    }

    private fun moveBy(days: Long) {
        _state.update {
            it.copy(date = it.date.plusDays(days), followToday = false, hidden = emptySet())
        }
        load()
    }

    private fun stepDays(): Long = if (_state.value.period == Period.WEEK) 7 else 1

    private fun message(exc: ChartApiException): String =
        exc.message ?: "Server nicht erreichbar"
}
