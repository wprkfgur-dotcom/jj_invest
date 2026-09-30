package com.example.jongjongtrader.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.theme.*
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

@Composable
fun InteractiveLineChart(
    values: List<Double>,
    dates: List<String>,
    lineColor: Color = AccentBlue,
    modifier: Modifier = Modifier.fillMaxWidth().height(200.dp),
    secondaryValues: List<Double>? = null,
    secondaryColor: Color = TextSecondary
) {
    if (values.isEmpty()) {
        Box(modifier = modifier, contentAlignment = androidx.compose.ui.Alignment.Center) {
            Text("기록된 차트 데이터가 없습니다.", color = TextMuted, fontSize = 12.sp)
        }
        return
    }

    var selectedIndex by remember { mutableStateOf<Int?>(null) }
    var zoomScale by remember { mutableStateOf(1.0f) }
    var panOffset by remember { mutableStateOf(0.0f) }

    val allVals = values + (secondaryValues ?: emptyList())
    val rawMin = allVals.minOrNull() ?: 0.0
    val rawMax = allVals.maxOrNull() ?: 1000.0
    val minVal = if (rawMin == rawMax) max(0.0, rawMin * 0.9) else rawMin
    val maxVal = if (rawMin == rawMax) rawMax * 1.1 else rawMax
    val valRange = if (maxVal > minVal) maxVal - minVal else 1.0

    Column(modifier = Modifier.fillMaxWidth()) {
        if (selectedIndex != null && selectedIndex!! in values.indices) {
            val idx = selectedIndex!!
            val dateStr = if (idx in dates.indices) dates[idx] else ""
            val valStr = String.format(Locale.US, "$%,.2f", values[idx])
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 2.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(text = "일자: $dateStr", color = TextSecondary, fontSize = 11.sp)
                Text(text = "자산: $valStr", color = lineColor, fontSize = 11.sp)
            }
        }

        Canvas(
            modifier = modifier
                .pointerInput(values) {
                    detectTapGestures(
                        onPress = { offset ->
                            val n = values.size
                            if (n > 1) {
                                val ratio = (offset.x / size.width).coerceIn(0f, 1f)
                                selectedIndex = (ratio * (n - 1)).toInt()
                            }
                        }
                    )
                }
                .pointerInput(Unit) {
                    detectTransformGestures { _, pan, zoom, _ ->
                        zoomScale = (zoomScale * zoom).coerceIn(1.0f, 4.0f)
                        panOffset += pan.x
                    }
                }
        ) {
            val w = size.width
            val h = size.height
            val padBottom = 24.dp.toPx()
            val padTop = 16.dp.toPx()
            val chartH = h - padBottom - padTop

            // Grid lines
            val gridSteps = listOf(0.0f, 0.5f, 1.0f)
            for (step in gridSteps) {
                val y = padTop + chartH * (1.0f - step)
                drawLine(
                    color = BorderColor,
                    start = Offset(0f, y),
                    end = Offset(w, y),
                    strokeWidth = 1.dp.toPx(),
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 10f), 0f)
                )
            }

            // Path calculation
            val n = values.size
            fun getOffset(i: Int, v: Double): Offset {
                val x = (i.toFloat() / max(1, n - 1)) * w
                val y = padTop + chartH - (((v - minVal) / valRange).toFloat() * chartH)
                return Offset(x, y)
            }

            // Secondary line (e.g. Buy & Hold)
            if (secondaryValues != null && secondaryValues.size == n) {
                val secPath = Path().apply {
                    val p0 = getOffset(0, secondaryValues[0])
                    moveTo(p0.x, p0.y)
                    for (i in 1 until n) {
                        val pt = getOffset(i, secondaryValues[i])
                        lineTo(pt.x, pt.y)
                    }
                }
                drawPath(
                    path = secPath,
                    color = secondaryColor,
                    style = Stroke(
                        width = 1.8.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f), 0f)
                    )
                )
            }

            // Primary line
            val linePath = Path()
            val fillPath = Path()
            val firstPt = getOffset(0, values[0])

            linePath.moveTo(firstPt.x, firstPt.y)
            fillPath.moveTo(firstPt.x, padTop + chartH)
            fillPath.lineTo(firstPt.x, firstPt.y)

            for (i in 1 until n) {
                val pt = getOffset(i, values[i])
                linePath.lineTo(pt.x, pt.y)
                fillPath.lineTo(pt.x, pt.y)
            }

            val lastPt = getOffset(n - 1, values.last())
            fillPath.lineTo(lastPt.x, padTop + chartH)
            fillPath.close()

            // Draw Area Gradient Fill
            drawPath(
                path = fillPath,
                brush = Brush.verticalGradient(
                    colors = listOf(lineColor.copy(alpha = 0.35f), lineColor.copy(alpha = 0.02f)),
                    startY = padTop,
                    endY = padTop + chartH
                )
            )

            // Draw Main Stroke
            drawPath(
                path = linePath,
                color = lineColor,
                style = Stroke(width = 2.5.dp.toPx())
            )

            // Draw Selected Scrub Line & Dot
            if (selectedIndex != null && selectedIndex!! in values.indices) {
                val selPt = getOffset(selectedIndex!!, values[selectedIndex!!])
                drawLine(
                    color = TextPrimary.copy(alpha = 0.6f),
                    start = Offset(selPt.x, padTop),
                    end = Offset(selPt.x, padTop + chartH),
                    strokeWidth = 1.dp.toPx()
                )
                drawCircle(color = TextPrimary, radius = 5.dp.toPx(), center = selPt)
                drawCircle(color = lineColor, radius = 3.dp.toPx(), center = selPt)
            }
        }
    }
}
