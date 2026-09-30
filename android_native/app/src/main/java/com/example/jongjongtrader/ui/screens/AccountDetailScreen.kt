package com.example.jongjongtrader.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.domain.InfiniteBuyingEngine
import com.example.jongjongtrader.domain.JongJongEngine
import com.example.jongjongtrader.theme.*
import com.example.jongjongtrader.ui.components.OrderSectionBoxes
import com.example.jongjongtrader.ui.components.SettlementDialog
import java.util.Locale

@OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)
@Composable
fun AccountDetailScreen(
    account: Account,
    currentPrice: Double = 35.0,
    onBack: () -> Unit,
    onAccountUpdated: (Account) -> Unit
) {
    val scrollState = rememberScrollState()
    var showSettleDialog by remember { mutableStateOf(false) }

    val orderPlan = remember(account, currentPrice) {
        if (account.strategy.contains("무한매수")) {
            InfiniteBuyingEngine.calculateOrders(account, currentPrice)
        } else {
            JongJongEngine.calculateOrders(account, currentPrice)
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
        // Top Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로가기", tint = TextPrimary)
            }
            Spacer(modifier = Modifier.width(4.dp))
            Column {
                Text(account.name, color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Text("${account.ticker} • ${account.strategy}", color = TextSecondary, fontSize = 12.sp)
            }
        }

        // Summary Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = SurfaceCard),
            shape = RoundedCornerShape(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("총 시드", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", account.totalSeed), color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    }
                    Column {
                        Text("위기준비금", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", account.crisisReserve), color = AccentBlue, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    }
                    Column {
                        Text("실가동 시드", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", account.activeSeed), color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    }
                }
                HorizontalDivider(color = BorderColor.copy(alpha = 0.4f), thickness = 1.dp)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("현재 현금", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", account.currentCash), color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                    Column {
                        Text("총 매입금", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%,.0f", account.totalInvested), color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                    Column {
                        Text("평균 단가", color = TextMuted, fontSize = 10.sp)
                        Text(String.format(Locale.US, "$%.2f", account.averagePrice), color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        // Action Buttons: 일일 정산
        Button(
            onClick = { showSettleDialog = true },
            modifier = Modifier.fillMaxWidth().height(48.dp),
            colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("일일 정산 실행", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        }

        // 매수 / 매도 주문표 (분리된 박스)
        OrderSectionBoxes(
            buyOrders = orderPlan.buyOrders,
            sellOrders = orderPlan.sellOrders
        )

        // 매입 조각별 현황
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("매입 조각별 현황 (${account.lots.size}개 조각)", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            if (account.lots.isEmpty()) {
                Surface(
                    color = SurfaceCard,
                    shape = RoundedCornerShape(10.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor),
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
                ) {
                    Text("현재 매입된 조각이 없습니다.", color = TextMuted, fontSize = 12.sp, modifier = Modifier.padding(16.dp))
                }
            } else {
                for (lot in account.lots) {
                    val pDiff = currentPrice - lot.buyPrice
                    val pRate = if (lot.buyPrice > 0) (pDiff / lot.buyPrice) * 100.0 else 0.0
                    val pColor = if (pRate >= 0) ProfitGreen else LossRed
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(SurfaceCard, RoundedCornerShape(8.dp))
                            .border(1.dp, BorderColor, RoundedCornerShape(8.dp))
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("${lot.index}회차 (${lot.shares}주)", color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        Text("매수가: $${String.format(Locale.US, "%.2f", lot.buyPrice)}", color = TextSecondary, fontSize = 11.sp)
                        Text(String.format(Locale.US, "%+.2f%%", pRate), color = pColor, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // 최근 거래 내역 (엑셀 형식)
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("최근 거래 내역 (길게 탭하여 수정)", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            if (account.history.isEmpty()) {
                Surface(
                    color = SurfaceCard,
                    shape = RoundedCornerShape(10.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor),
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
                ) {
                    Text("기록된 거래 내역이 없습니다.", color = TextMuted, fontSize = 12.sp, modifier = Modifier.padding(16.dp))
                }
            } else {
                for (tx in account.history.take(15)) {
                    val isBuy = tx.type == "매수"
                    val tColor = if (isBuy) AccentBlue else ProfitGreen
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(SurfaceCard, RoundedCornerShape(8.dp))
                            .border(1.dp, BorderColor, RoundedCornerShape(8.dp))
                            .padding(10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("${tx.date} • ${tx.type}", color = tColor, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            Text("${tx.shares}주 @ $${String.format(Locale.US, "%.2f", tx.price)}", color = TextSecondary, fontSize = 10.sp)
                        }
                        Text(String.format(Locale.US, "$%,.2f", tx.amount), color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }

    if (showSettleDialog) {
        SettlementDialog(
            account = account,
            currentPrice = currentPrice,
            onDismiss = { showSettleDialog = false },
            onSettle = { closeP, buyQty, sellQty ->
                val updated = JongJongEngine.executeDailySettlement(account, closeP, buyQty, sellQty)
                onAccountUpdated(updated)
                showSettleDialog = false
            }
        )
    }
}
