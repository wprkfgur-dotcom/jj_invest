package com.example.jongjongtrader.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.OrderItem
import com.example.jongjongtrader.theme.*
import java.util.Locale

@Composable
fun OrderSectionBoxes(
    buyOrders: List<OrderItem>,
    sellOrders: List<OrderItem>,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        // 1. Sell Orders Box
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(SurfaceCard, RoundedCornerShape(12.dp))
                .border(1.dp, ProfitGreen.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("매도 주문표 (익절/대기)", color = ProfitGreen, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text("${sellOrders.size}건", color = TextSecondary, fontSize = 11.sp)
            }

            if (sellOrders.isEmpty()) {
                Text("대기 중인 매도 주문이 없습니다.", color = TextMuted, fontSize = 12.sp, modifier = Modifier.padding(vertical = 4.dp))
            } else {
                for (item in sellOrders) {
                    val rateStr = String.format(Locale.US, "(%+.1f%%)", item.changeRate)
                    val priceStr = String.format(Locale.US, "$%.2f", item.price)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(SurfaceElevated.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                            .padding(horizontal = 10.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(item.stage, color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("$priceStr 에 ${item.shares}주", color = ProfitGreen, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Text(rateStr, color = ProfitGreen.copy(alpha = 0.8f), fontSize = 11.sp)
                        }
                    }
                }
            }
        }

        // 2. Buy Orders Box
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(SurfaceCard, RoundedCornerShape(12.dp))
                .border(1.dp, AccentBlue.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("매수 주문표 (분할 LOC)", color = AccentBlue, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text("${buyOrders.size}건", color = TextSecondary, fontSize = 11.sp)
            }

            if (buyOrders.isEmpty()) {
                Text("대기 중인 매수 주문이 없습니다.", color = TextMuted, fontSize = 12.sp, modifier = Modifier.padding(vertical = 4.dp))
            } else {
                for (item in buyOrders) {
                    val rateStr = String.format(Locale.US, "(%+.1f%%)", item.changeRate)
                    val priceStr = String.format(Locale.US, "$%.2f", item.price)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(SurfaceElevated.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                            .padding(horizontal = 10.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(item.stage, color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("$priceStr 에 ${item.shares}주", color = AccentBlue, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Text(rateStr, color = TextSecondary, fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}
