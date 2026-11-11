package de.zwotzie.heizung.ui.chart

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import de.zwotzie.heizung.data.ChartRow
import de.zwotzie.heizung.data.MetricId
import de.zwotzie.heizung.data.TabSpec
import de.zwotzie.heizung.data.ViewWindow
import de.zwotzie.heizung.ui.SensorColors
import kotlin.math.roundToInt

private val TextColor = Color(0xFF9A9A9A)
private val GridColor = Color(0xFF222222)
private val AxisColor = Color(0xFF3A3A3A)

/**
 * Zeichnet einen Reiter: Temperaturkurven oben, je eine Zeile für Serien mit
 * anderer Einheit, darunter die Digitalbänder.
 */
@Composable
fun ChartCanvas(
    spec: TabSpec,
    rows: List<ChartRow>,
    window: ViewWindow,
    hidden: Set<MetricId>,
    labels: List<Pair<Long, String>>,
    onPan: (Long) -> Unit,
    onZoom: (Double, Long) -> Unit,
    onReset: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val textMeasurer = rememberTextMeasurer()
    val currentWindow by rememberUpdatedState(window)
    val currentOnPan by rememberUpdatedState(onPan)
    val currentOnZoom by rememberUpdatedState(onZoom)
    val currentOnReset by rememberUpdatedState(onReset)

    Canvas(
        modifier = modifier
            .pointerInput(Unit) {
                detectTransformGestures { centroid, pan, zoom, _ ->
                    val window = currentWindow
                    val plotWidth = size.width - Y_AXIS_WIDTH.dp.toPx()
                    if (plotWidth <= 0f) return@detectTransformGestures

                    if (zoom != 1f) {
                        val fraction = (centroid.x / plotWidth).coerceIn(0f, 1f)
                        val anchor = window.startSec + (window.spanSec * fraction).toLong()
                        currentOnZoom(zoom.toDouble(), anchor)
                    }
                    if (pan.x != 0f) {
                        val secPerPx = window.spanSec.toDouble() / plotWidth
                        currentOnPan(-(pan.x * secPerPx).toLong())
                    }
                }
            }
            .pointerInput(Unit) {
                detectTapGestures(onDoubleTap = { currentOnReset() })
            },
    ) {
        drawTabs(spec, rows, window, hidden, labels, textMeasurer)
    }
}

private const val Y_AXIS_WIDTH = 44f

private fun DrawScope.drawTabs(
    spec: TabSpec,
    rows: List<ChartRow>,
    window: ViewWindow,
    hidden: Set<MetricId>,
    labels: List<Pair<Long, String>>,
    textMeasurer: TextMeasurer,
) {
    if (rows.isEmpty() || window.spanSec <= 0L) return

    val yAxisWidth = Y_AXIS_WIDTH.dp.toPx()
    val plotLeft = 0f
    val plotRight = size.width - yAxisWidth
    if (plotRight <= 0f) return

    val topPad = 6.dp.toPx()
    val labelHeight = 18.dp.toPx()
    val digitalRow = 9.dp.toPx()
    val digitalGap = 3.dp.toPx()
    val secondaryRow = 34.dp.toPx()
    val secondaryGap = 8.dp.toPx()

    val digitalZone = spec.digital.size * (digitalRow + digitalGap)
    val secondaryZone = spec.rows.size * (secondaryRow + secondaryGap)
    val chartBottom = size.height - labelHeight
    val tempsBottom = (chartBottom - digitalZone - secondaryZone).coerceAtLeast(topPad + 40f)

    val visible = rows.filter { it.timestampSec in window.startSec..window.endSec }
    val drawRows = if (visible.size >= 2) visible else rows

    val xOf = { sec: Long ->
        val fraction = (sec - window.startSec).toDouble() / window.spanSec
        (plotLeft + (fraction * (plotRight - plotLeft)).toFloat()).coerceIn(plotLeft, plotRight)
    }

    // ── Temperaturbereich ────────────────────────────────────────────────────
    val shownTemps = spec.temperatures.filter { it !in hidden }
    val range = ChartScale.range(
        values = shownTemps.flatMap { metric -> drawRows.map { it.values[metric] } },
        minSpan = 5.0,
    )

    for (step in 0..3) {
        val value = range.start + (range.endInclusive - range.start) * step / 3.0
        val y = ChartScale.yOf(value, range, topPad, tempsBottom)
        drawLine(GridColor, Offset(plotLeft, y), Offset(plotRight, y), strokeWidth = 1f)
        drawText(
            textMeasurer = textMeasurer,
            text = "${value.roundToInt()}°",
            topLeft = Offset(plotRight + 4.dp.toPx(), y - 6.dp.toPx()),
            style = TextStyle(color = TextColor, fontSize = 10.sp),
        )
    }

    for (metric in shownTemps) {
        drawSeries(drawRows, metric, xOf, chartBottom = tempsBottom, top = topPad, range, SensorColors.of(metric))
    }

    drawLine(AxisColor, Offset(plotLeft, tempsBottom), Offset(plotRight, tempsBottom), strokeWidth = 1f)

    // ── Zeilen mit eigener Einheit ───────────────────────────────────────────
    var rowTop = tempsBottom + secondaryGap
    for (metric in spec.rows.filter { it !in hidden }) {
        val rowBottom = rowTop + secondaryRow
        val values = drawRows.map { it.values[metric] }
        val max = values.filterNotNull().filter { it.isFinite() }.maxOrNull() ?: 100.0
        val rowRange = 0.0..(if (max <= 0.0) 1.0 else max)

        drawLine(GridColor, Offset(plotLeft, rowBottom), Offset(plotRight, rowBottom), strokeWidth = 1f)
        drawSeries(drawRows, metric, xOf, chartBottom = rowBottom, top = rowTop, rowRange, SensorColors.of(metric))
        rowTop = rowBottom + secondaryGap
    }

    // ── Digitalbänder ────────────────────────────────────────────────────────
    var digitalTop = tempsBottom + secondaryZone + digitalGap
    for (metric in spec.digital.filter { it !in hidden }) {
        val rowBottom = digitalTop + digitalRow
        drawLine(GridColor, Offset(plotLeft, rowBottom), Offset(plotRight, rowBottom), strokeWidth = 1f)
        drawDigital(drawRows, metric, xOf, digitalTop, rowBottom)
        digitalTop = rowBottom + digitalGap
    }

    // ── Zeitachse ────────────────────────────────────────────────────────────
    for ((sec, text) in labels) {
        val x = xOf(sec)
        drawLine(AxisColor, Offset(x, chartBottom), Offset(x, chartBottom + 3.dp.toPx()), strokeWidth = 1f)
        drawText(
            textMeasurer = textMeasurer,
            text = text,
            topLeft = Offset(x + 3.dp.toPx(), chartBottom + 3.dp.toPx()),
            style = TextStyle(color = TextColor, fontSize = 9.sp),
        )
    }
}

private fun DrawScope.drawSeries(
    rows: List<ChartRow>,
    metric: MetricId,
    xOf: (Long) -> Float,
    chartBottom: Float,
    top: Float,
    range: ClosedFloatingPointRange<Double>,
    color: Color,
) {
    val path = Path()
    var started = false

    for (row in rows) {
        val value = row.values[metric]
        if (value == null || !value.isFinite()) {
            started = false
            continue
        }
        val x = xOf(row.timestampSec)
        val y = ChartScale.yOf(value, range, top, chartBottom)
        if (started) path.lineTo(x, y) else path.moveTo(x, y).also { started = true }
    }
    drawPath(path, color, style = androidx.compose.ui.graphics.drawscope.Stroke(width = 2.dp.toPx()))
}

private fun DrawScope.drawDigital(
    rows: List<ChartRow>,
    metric: MetricId,
    xOf: (Long) -> Float,
    top: Float,
    bottom: Float,
) {
    val path = Path()
    var started = false
    var lastX = 0f
    var lastY = bottom

    for (row in rows) {
        val value = row.values[metric]
        if (value == null) {
            started = false
            continue
        }
        val x = xOf(row.timestampSec)
        val y = if (value >= 0.5) top else bottom
        if (!started) {
            path.moveTo(x, bottom)
            path.lineTo(x, y)
            started = true
        } else {
            path.lineTo(x, lastY)
            path.lineTo(x, y)
        }
        lastX = x
        lastY = y
    }

    if (!started) return

    val outline = Path().apply {
        addPath(path)
        lineTo(lastX, bottom)
        close()
    }
    drawPath(outline, Color(0xFF34D399).copy(alpha = 0.35f))
    drawPath(path, Color(0xFF34D399), style = androidx.compose.ui.graphics.drawscope.Stroke(width = 1.dp.toPx()))
}
