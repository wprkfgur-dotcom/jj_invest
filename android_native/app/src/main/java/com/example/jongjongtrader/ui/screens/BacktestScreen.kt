package com.example.jongjongtrader.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.BacktestMetric
import com.example.jongjongtrader.domain.BacktestEngine
import com.example.jongjongtrader.theme.*
import com.example.jongjongtrader.ui.components.InteractiveLineChart
import java.util.Locale

@Composable
fun BacktestScreen() {
    val scrollState = rememberScrollState()

    var ticker by remember { mutableStateOf("SOXL") }
    var strategyName by remember { mutableStateOf("종종전략") }
    var seedStr by remember { mutableStateOf("50000") }
    var isRunning by remember { mutableStateOf(false) }
    var resultMetric by remember { mutableStateOf<BacktestMetric?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDark)
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("전략 시뮬레이션 및 백테스트", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)

        // Configuration Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = SurfaceCard),
            shape = RoundedCornerShape(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = ticker,
                        onValueChange = { ticker = it.uppercase() },
                        label = { Text("티커") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = strategyName,
                        onValueChange = { strategyName = it },
                        label = { Text("전략") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                }
                OutlinedTextField(
                    value = seedStr,
                    onValueChange = { seedStr = it },
                    label = { Text("초기 자본금 ($)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Button(
                    onClick = {
                        isRunning = true
                        val seed = seedStr.toDoubleOrNull() ?: 50000.0
                        val candles = BacktestEngine.generateSampleCandles(ticker, 180)
                        val metric = BacktestEngine.runBacktest(ticker, strategyName, seed, candles)
                        resultMetric = metric
                        isRunning = false
                    },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
                    shape = RoundedCornerShape(12.dp),
                    enabled = !isRunning
                ) {
                    if (isRunning) {
                        CircularProgressIndicator(color = TextPrimary, modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    } else {
                        Text("백테스트 실행", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Results Section
        val res = resultMetric
        if (res != null) {
            Text("백테스트 결과 분석", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold)

            // Metrics Grid
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Card(
                    modifier = Modifier.weight(1f),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("최종 자산", color = TextMuted, fontSize = 11.sp)
                        Text(String.format(Locale.US, "$%,.0f", res.finalAsset), color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        val pSign = if (res.totalReturn >= 0) "+" else ""
                        val pColor = if (res.totalReturn >= 0) ProfitGreen else LossRed
                        Text("$pSign${String.format(Locale.US, "%.1f%%", res.totalReturn)}", color = pColor, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }
                }

                Card(
                    modifier = Modifier.weight(1f),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("연평균 수익률 (CAGR)", color = TextMuted, fontSize = 11.sp)
                        Text(String.format(Locale.US, "%.1f%%", res.cagr), color = ProfitGreen, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        Text("MDD: ${String.format(Locale.US, "%.1f%%", res.mdd)}", color = LossRed, fontSize = 11.sp)
                    }
                }

                Card(
                    modifier = Modifier.weight(1f),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("승률 (Win Rate)", color = TextMuted, fontSize = 11.sp)
                        Text(String.format(Locale.US, "%.1f%%", res.winRate), color = AccentBlue, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        Text("안정적 회전", color = TextSecondary, fontSize = 11.sp)
                    }
                }
            }

            // Comparison Chart
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                shape = RoundedCornerShape(16.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("전략 vs 단순보유 비교", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Box(modifier = Modifier.size(8.dp).background(ProfitGreen, RoundedCornerShape(2.dp)))
                                Text(res.stratName, color = ProfitGreen, fontSize = 10.sp)
                            }
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Box(modifier = Modifier.size(8.dp).background(TextSecondary, RoundedCornerShape(2.dp)))
                                Text("${res.ticker} 보유", color = TextSecondary, fontSize = 10.sp)
                            }
                        }
                    }

                    InteractiveLineChart(
                        values = res.stratAssets,
                        dates = res.dates,
                        lineColor = ProfitGreen,
                        secondaryValues = res.bnhAssets,
                        secondaryColor = TextSecondary,
                        modifier = Modifier.fillMaxWidth().height(180.dp)
                    )
                }
            }
        }
    }
}
