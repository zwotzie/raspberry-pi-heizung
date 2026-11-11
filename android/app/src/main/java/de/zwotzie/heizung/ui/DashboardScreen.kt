package de.zwotzie.heizung.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import de.zwotzie.heizung.data.Catalog
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.Period
import de.zwotzie.heizung.data.TabSpec
import de.zwotzie.heizung.data.TimeWindow
import de.zwotzie.heizung.ui.chart.ChartCanvas
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Aktionen des Hauptbildschirms. */
sealed interface DashboardEvent {
    data class SetPeriod(val period: Period) : DashboardEvent
    data object Previous : DashboardEvent
    data object Next : DashboardEvent
    data object Today : DashboardEvent
    data class SelectTab(val index: Int) : DashboardEvent
    data class ToggleSeries(val metric: MetricId) : DashboardEvent
    data class Pan(val deltaSec: Long) : DashboardEvent
    data class Zoom(val factor: Double, val anchorSec: Long) : DashboardEvent
    data object ResetZoom : DashboardEvent
    data object Retry : DashboardEvent
    data object OpenSettings : DashboardEvent
}

private val zone = ZoneId.of("Europe/Berlin")
private val dateFormat = DateTimeFormatter.ofPattern("EEE, d. MMM", Locale.GERMAN)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(state: DashboardState, onEvent: (DashboardEvent) -> Unit) {
    val spec = Catalog.tabs[state.tabIndex.coerceIn(0, Catalog.tabs.lastIndex)]
    val labels = remember(state.window, state.period) {
        state.window?.let { TimeWindow.tickLabels(it, state.period, zone) } ?: emptyList()
    }

    Scaffold(
        containerColor = Color.Black,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Heizung", fontWeight = FontWeight.SemiBold)
                        Text(
                            text = state.date.format(dateFormat),
                            fontSize = 12.sp,
                            color = Color(0xFF8A8A8A),
                        )
                    }
                },
                actions = {
                    TextButton(onClick = { onEvent(DashboardEvent.Retry) }) { Text("⟳") }
                    TextButton(onClick = { onEvent(DashboardEvent.OpenSettings) }) { Text("⚙") }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Black,
                    titleContentColor = Color(0xFFDFDFDF),
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(horizontal = 8.dp),
        ) {
            PeriodControls(state.period, onEvent)
            PrimaryTabRow(selectedTabIndex = state.tabIndex, containerColor = Color.Black) {
                Catalog.tabs.forEachIndexed { index, tab ->
                    Tab(
                        selected = index == state.tabIndex,
                        onClick = { onEvent(DashboardEvent.SelectTab(index)) },
                        text = { Text(tab.title, fontSize = 13.sp) },
                    )
                }
            }

            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                when {
                    state.error != null -> MessageState(state.error, "Erneut versuchen") {
                        onEvent(DashboardEvent.Retry)
                    }
                    state.window == null && !state.loading -> MessageState(
                        "Keine Daten für diesen Tag",
                        null,
                        null,
                    )
                    state.window != null -> ChartCanvas(
                        spec = spec,
                        rows = state.rows,
                        window = state.window,
                        hidden = state.hidden,
                        labels = labels,
                        onPan = { onEvent(DashboardEvent.Pan(it)) },
                        onZoom = { factor, anchor -> onEvent(DashboardEvent.Zoom(factor, anchor)) },
                        onReset = { onEvent(DashboardEvent.ResetZoom) },
                        modifier = Modifier.fillMaxSize(),
                    )
                }
                if (state.loading) {
                    LinearProgressIndicator(
                        modifier = Modifier.align(Alignment.TopCenter).fillMaxWidth(),
                    )
                }
            }

            LegendChips(spec, state.hidden) { onEvent(DashboardEvent.ToggleSeries(it)) }
        }
    }
}

@Composable
private fun PeriodControls(period: Period, onEvent: (DashboardEvent) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        SingleChoiceSegmentedButtonRow {
            SegmentedButton(
                selected = period == Period.DAY,
                onClick = { onEvent(DashboardEvent.SetPeriod(Period.DAY)) },
                shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2),
            ) { Text("Tag", fontSize = 12.sp) }
            SegmentedButton(
                selected = period == Period.WEEK,
                onClick = { onEvent(DashboardEvent.SetPeriod(Period.WEEK)) },
                shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2),
            ) { Text("Woche", fontSize = 12.sp) }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = { onEvent(DashboardEvent.Previous) }) { Text("◀", fontSize = 14.sp) }
            TextButton(onClick = { onEvent(DashboardEvent.Today) }) { Text("Heute", fontSize = 12.sp) }
            TextButton(onClick = { onEvent(DashboardEvent.Next) }) { Text("▶", fontSize = 14.sp) }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun LegendChips(spec: TabSpec, hidden: Set<MetricId>, onToggle: (MetricId) -> Unit) {
    FlowRow(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        LegendEntries.of(spec).forEach { entry ->
            val isHidden = entry.metric in hidden
            Row(
                modifier = Modifier
                    .background(Color(0xFF121212), RoundedCornerShape(8.dp))
                    .clickable { onToggle(entry.metric) }
                    .padding(horizontal = 6.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(7.dp)
                        .background(
                            color = if (isHidden) entry.color.copy(alpha = 0.3f) else entry.color,
                            shape = CircleShape,
                        ),
                )
                Text(
                    text = entry.label,
                    fontSize = 10.sp,
                    color = if (isHidden) Color(0xFF6B6B6B) else Color(0xFFC9C9C9),
                )
            }
        }
    }
}

@Composable
private fun MessageState(text: String, action: String?, onAction: (() -> Unit)?) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text, fontSize = 13.sp, color = Color(0xFF9A9A9A), textAlign = TextAlign.Center)
        if (action != null && onAction != null) {
            Button(onClick = onAction, modifier = Modifier.padding(top = 12.dp)) { Text(action) }
        }
    }
}
