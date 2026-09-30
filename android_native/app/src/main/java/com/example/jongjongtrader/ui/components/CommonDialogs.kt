package com.example.jongjongtrader.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.data.model.Transaction
import com.example.jongjongtrader.theme.*
import java.util.Locale

@Composable
fun AddAccountDialog(
    onDismiss: () -> Unit,
    onConfirm: (Account) -> Unit
) {
    var name by remember { mutableStateOf("SOXL 종종 1호") }
    var ticker by remember { mutableStateOf("SOXL") }
    var strategy by remember { mutableStateOf("종종전략") }
    var totalSeedStr by remember { mutableStateOf("10000") }
    var crisisRatioStr by remember { mutableStateOf("5") }
    var targetProfitStr by remember { mutableStateOf("3") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("신규 투자 계좌 등록", color = TextPrimary, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("계좌 이름") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = ticker,
                        onValueChange = { ticker = it.uppercase() },
                        label = { Text("티커 (예: SOXL)") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = strategy,
                        onValueChange = { strategy = it },
                        label = { Text("전략") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                }
                OutlinedTextField(
                    value = totalSeedStr,
                    onValueChange = { totalSeedStr = it },
                    label = { Text("총 시드 ($)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = crisisRatioStr,
                        onValueChange = { crisisRatioStr = it },
                        label = { Text("위기준비금 (%)") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = targetProfitStr,
                        onValueChange = { targetProfitStr = it },
                        label = { Text("목표 수익률 (%)") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val seed = totalSeedStr.toDoubleOrNull() ?: 10000.0
                    val crisisRatio = (crisisRatioStr.toDoubleOrNull() ?: 5.0) / 100.0
                    val profitRate = (targetProfitStr.toDoubleOrNull() ?: 3.0) / 100.0
                    val cash = seed * (1.0 - crisisRatio)
                    val newAcc = Account(
                        name = name,
                        ticker = ticker,
                        strategy = strategy,
                        totalSeed = seed,
                        crisisReserveRatio = crisisRatio,
                        targetProfitRate = profitRate,
                        currentCash = cash
                    )
                    onConfirm(newAcc)
                },
                colors = ButtonDefaults.buttonColors(containerColor = AccentBlue)
            ) {
                Text("계좌 생성", color = TextPrimary)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("취소", color = TextSecondary)
            }
        },
        containerColor = SurfaceCard
    )
}

@Composable
fun SettlementDialog(
    account: Account,
    currentPrice: Double,
    onDismiss: () -> Unit,
    onSettle: (closePrice: Double, buyShares: Int, sellShares: Int) -> Unit
) {
    var closePriceStr by remember { mutableStateOf(String.format(Locale.US, "%.2f", currentPrice)) }
    var buySharesStr by remember { mutableStateOf("0") }
    var sellSharesStr by remember { mutableStateOf("0") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("일일 정산", color = TextPrimary, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("${account.name} (${account.ticker})의 당일 체결 내역을 입력합니다.", color = TextSecondary, fontSize = 12.sp)
                OutlinedTextField(
                    value = closePriceStr,
                    onValueChange = { closePriceStr = it },
                    label = { Text("당일 종가 ($)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = buySharesStr,
                        onValueChange = { buySharesStr = it },
                        label = { Text("체결 매수량(주)") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = sellSharesStr,
                        onValueChange = { sellSharesStr = it },
                        label = { Text("체결 매도량(주)") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val p = closePriceStr.toDoubleOrNull() ?: currentPrice
                    val b = buySharesStr.toIntOrNull() ?: 0
                    val s = sellSharesStr.toIntOrNull() ?: 0
                    onSettle(p, b, s)
                },
                colors = ButtonDefaults.buttonColors(containerColor = AccentBlue)
            ) {
                Text("정산 완료", color = TextPrimary)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("취소", color = TextSecondary)
            }
        },
        containerColor = SurfaceCard
    )
}
