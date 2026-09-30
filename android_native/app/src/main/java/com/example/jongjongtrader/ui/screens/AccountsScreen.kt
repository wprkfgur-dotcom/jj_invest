package com.example.jongjongtrader.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.theme.*
import com.example.jongjongtrader.ui.components.AddAccountDialog
import java.util.Locale

@Composable
fun AccountsScreen(
    accounts: List<Account>,
    currentPrices: Map<String, Double> = emptyMap(),
    onAccountClick: (Account) -> Unit,
    onAddAccount: (Account) -> Unit
) {
    var showAddDialog by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize().background(BgDark)) {
        if (accounts.isEmpty()) {
            Column(
                modifier = Modifier.fillMaxSize().padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text("등록된 계좌가 없습니다.", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
                Text("우측 하단의 (+) 버튼을 눌러 새 계좌를 추가하세요.", color = TextSecondary, fontSize = 13.sp)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                items(accounts) { acc ->
                    val curPrice = currentPrices[acc.ticker] ?: acc.averagePrice.takeIf { it > 0 } ?: 35.0
                    val totAsset = acc.calculateTotalAsset(curPrice)
                    val profit = acc.calculateProfit(curPrice)
                    val profitRate = acc.calculateProfitRate(curPrice)
                    val pColor = if (profit >= 0) ProfitGreen else LossRed
                    val pSign = if (profit >= 0) "+" else ""

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onAccountClick(acc) },
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
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Surface(
                                        color = AccentBlue.copy(alpha = 0.15f),
                                        shape = RoundedCornerShape(8.dp),
                                        border = androidx.compose.foundation.BorderStroke(1.dp, AccentBlue.copy(alpha = 0.3f))
                                    ) {
                                        Text(acc.ticker, color = AccentBlue, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp))
                                    }
                                    Text(acc.name, color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                                }
                                Text(acc.strategy, color = TextSecondary, fontSize = 11.sp)
                            }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Bottom
                            ) {
                                Column {
                                    Text("평가 자산", color = TextMuted, fontSize = 10.sp)
                                    Text(String.format(Locale.US, "$%,.0f", totAsset), color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text("평가 손익", color = TextMuted, fontSize = 10.sp)
                                    Text("$pSign${String.format(Locale.US, "%,.0f", profit)} ($pSign${String.format(Locale.US, "%.2f", profitRate)}%)", color = pColor, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                                }
                            }

                            HorizontalDivider(color = BorderColor.copy(alpha = 0.4f), thickness = 1.dp)

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text("보유 ${acc.totalShares}주", color = TextSecondary, fontSize = 11.sp)
                                Text("평단가: $${String.format(Locale.US, "%.2f", acc.averagePrice)}", color = TextSecondary, fontSize = 11.sp)
                                Text("현금: $${String.format(Locale.US, "%,.0f", acc.currentCash)}", color = TextSecondary, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }
        }

        // Circular (+) Floating Action Button at bottom right
        FloatingActionButton(
            onClick = { showAddDialog = true },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(20.dp),
            shape = CircleShape,
            containerColor = AccentBlue,
            contentColor = TextPrimary
        ) {
            Icon(imageVector = Icons.Default.Add, contentDescription = "계좌 추가")
        }

        if (showAddDialog) {
            AddAccountDialog(
                onDismiss = { showAddDialog = false },
                onConfirm = { newAcc ->
                    onAddAccount(newAcc)
                    showAddDialog = false
                }
            )
        }
    }
}
