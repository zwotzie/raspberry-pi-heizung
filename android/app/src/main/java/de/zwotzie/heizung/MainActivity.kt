package de.zwotzie.heizung

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import de.zwotzie.heizung.data.HttpChartApi
import de.zwotzie.heizung.data.Period
import de.zwotzie.heizung.data.ServerUrl
import de.zwotzie.heizung.data.SettingsStore
import de.zwotzie.heizung.ui.DashboardEvent
import de.zwotzie.heizung.ui.DashboardScreen
import de.zwotzie.heizung.ui.DashboardViewModel
import de.zwotzie.heizung.ui.SettingsScreen
import de.zwotzie.heizung.ui.theme.HeizungTheme
import kotlinx.coroutines.launch
import java.time.LocalDate

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val settings = SettingsStore(applicationContext)

        setContent {
            HeizungTheme {
                val scope = rememberCoroutineScope()
                val serverUrl by settings.serverUrl.collectAsStateWithLifecycle(initialValue = null)
                var settingsOpen by rememberSaveable { mutableStateOf(false) }

                val showSettings = serverUrl == null || settingsOpen

                if (showSettings) {
                    SettingsScreen(
                        current = serverUrl,
                        onSave = { raw ->
                            scope.launch {
                                settings.save(raw)
                                settingsOpen = false
                            }
                        },
                        onClose = { settingsOpen = false },
                        onTest = { raw ->
                            val normalized = ServerUrl.normalize(raw)
                            if (normalized == null) {
                                Result.failure(IllegalArgumentException("Ungültige Adresse"))
                            } else {
                                runCatching {
                                    HttpChartApi(baseUrl = { normalized })
                                        .fetch(LocalDate.now(), Period.DAY)
                                        .size
                                }
                            }
                        },
                    )
                    return@HeizungTheme
                }

                val viewModel: DashboardViewModel = viewModel(
                    key = "dashboard-$serverUrl",
                    factory = viewModelFactory {
                        initializer {
                            DashboardViewModel(
                                api = HttpChartApi(baseUrl = { serverUrl.orEmpty() }),
                                serverUrl = { serverUrl },
                            )
                        }
                    },
                )

                val state by viewModel.state.collectAsStateWithLifecycle()

                DashboardScreen(
                    state = state,
                    onEvent = { event ->
                        when (event) {
                            is DashboardEvent.SetPeriod -> viewModel.setPeriod(event.period)
                            DashboardEvent.Previous -> viewModel.previous()
                            DashboardEvent.Next -> viewModel.next()
                            DashboardEvent.Today -> viewModel.today()
                            is DashboardEvent.SelectTab -> viewModel.selectTab(event.index)
                            is DashboardEvent.ToggleSeries -> viewModel.toggleSeries(event.metric)
                            is DashboardEvent.Pan -> viewModel.pan(event.deltaSec)
                            is DashboardEvent.Zoom -> viewModel.zoom(event.factor, event.anchorSec)
                            DashboardEvent.ResetZoom -> viewModel.resetZoom()
                            DashboardEvent.Retry -> viewModel.retry()
                            DashboardEvent.OpenSettings -> settingsOpen = true
                        }
                    },
                )
            }
        }
    }
}
