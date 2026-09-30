package com.example.jongjongtrader.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.theme.*
import com.example.jongjongtrader.ui.components.InteractiveLineChart
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HomeScreen(
    accounts: List<Account>,
    currentPrices: Map<String, Double> = emptyMap()
) {
    val scrollState = rememberScrollState()

    var totalSeed = 0.0
    var totalAsset = 0.0
    var totalCash = 0.0
    var totalInvested = 0.0
    var totalCrisisReserve = 0.0

    for (acc in accounts) {
        val p = currentPrices[acc.ticker] ?: acc.averagePrice.takeIf { it > 0 } ?: 35.0
        totalSeed += acc.totalSeed
        totalCash += acc.currentCash
        totalInvested += acc.totalInvested
        totalCrisisReserve += acc.crisisReserve
        totalAsset += acc.calculateTotalAsset(p)
    }

    val totalProfit = totalAsset - totalSeed
    val totalProfitRate = if (totalSeed > 0) (totalProfit / totalSeed) * 100.0 else 0.0

    // Sample historical values for chart
    val dates = mutableListOf<String>()
    val chartValues = mutableListOf<Double>()
    val sdf = SimpleDateFormat("MM/dd", Locale.KOREA)
    val now = System.currentTimeMillis()
    val oneDay = 24L * 60 * 60 * 1000

    if (accounts.isEmpty()) {
        for (i in 4 downTo 0) {
            dates.add(sdf.format(Date(now - i * oneDay)))
            chartValues.add(0.0)
        }
    } else {
        for (i in 6 downTo 0) {
            dates.add(sdf.format(Date(now - i * oneDay)))
            val noise = 1.0 + (Math.sin(i * 0.5) * 0.015)
            chartValues.add(totalAsset * noise)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDark)
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // App Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text("JJ INVEST", color = AccentBlue, fontSize = 12.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
                Text("포트폴리오 종합 현황", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            }
            Surface(
                color = SurfaceCard,
                shape = RoundedCornerShape(20.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
            ) {
                Text(
                    text = "${accounts.size}개 계좌 운용 중",
                    color = TextSecondary,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                )
            }
        }

        // 1. Total Portfolio Asset Summary Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = SurfaceCard),
            shape = RoundedCornerShape(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
        ) {
            Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("전체 총 평가 자산", color = TextSecondary, fontSize = 12.sp)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Bottom
                ) {
                    Text(
                        text = String.format(Locale.US, "$%,.0f", totalAsset),
                        color = TextPrimary,
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold
                    )
                    val profitColor = if (totalProfit >= 0) ProfitGreen else LossRed
                    val sign = if (totalProfit >= 0) "+" else ""
                    Text(
                        text = "$sign${String.format(Locale.US, "%,.0f", totalProfit)} ($sign${String.format(Locale.US, "%.2f", totalProfitRate)}%)",
                        color = profitColor,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }

                HorizontalDivider(color = BorderColor.copy(alpha = 0.5f), thickness = 1.dp)

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("총 시드", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", totalSeed), color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                    Column {
                        Text("현금 잔액", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", totalCash), color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                    Column {
                        Text("위기준비금", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", totalCrisisReserve), color = AccentBlue, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        // 2. Growth Chart Card
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
                    Text("포트폴리오 성장 추이", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text("핀치: 확대 | 터치: 탐색", color = TextMuted, fontSize = 10.sp)
                }

                InteractiveLineChart(
                    values = chartValues,
                    dates = dates,
                    lineColor = AccentBlue,
                    modifier = Modifier.fillMaxWidth().height(180.dp)
                )
            }
        }
    }
}
