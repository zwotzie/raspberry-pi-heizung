package de.zwotzie.heizung

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import de.zwotzie.heizung.data.HttpChartApi
import de.zwotzie.heizung.data.SettingsStore
import de.zwotzie.heizung.ui.DashboardEvent
import de.zwotzie.heizung.ui.DashboardScreen
import de.zwotzie.heizung.ui.DashboardViewModel
import de.zwotzie.heizung.ui.theme.HeizungTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val settings = SettingsStore(applicationContext)

        setContent {
            HeizungTheme {
                val serverUrl by settings.serverUrl.collectAsStateWithLifecycle(initialValue = null)

                val viewModel: DashboardViewModel = viewModel(
                    key = "dashboard-${serverUrl ?: "leer"}",
                    factory = viewModelFactory {
                        initializer {
                            DashboardViewModel(
                                api = HttpChartApi(baseUrl = { serverUrl ?: "" }),
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
                            DashboardEvent.OpenSettings -> Unit
                        }
                    },
                )
            }
        }
    }
}
