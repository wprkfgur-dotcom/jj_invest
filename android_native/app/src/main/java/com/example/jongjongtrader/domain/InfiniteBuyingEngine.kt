package com.example.jongjongtrader.domain

import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.data.model.OrderItem
import java.util.Locale
import kotlin.math.*

object InfiniteBuyingEngine {

    fun calculateOrders(account: Account, currentPrice: Double): JongJongEngine.OrderPlan {
        if (currentPrice <= 0.0) {
            return JongJongEngine.OrderPlan(emptyList(), emptyList())
        }

        val totalDivisions = 40
        val currentT = min(totalDivisions - 1, account.lots.size)
        val remainingDivisions = max(1, totalDivisions - currentT)
        val dailyBudget = account.currentCash / remainingDivisions

        val isSoxl = account.ticker.contains("SOXL", ignoreCase = true)
        val starPct = if (isSoxl) (20.0 - currentT) / 100.0 else (15.0 - 0.75 * currentT) / 100.0
        val starPrice = floor((account.averagePrice * (1.0 + starPct)).coerceAtLeast(currentPrice * 0.9) * 100.0) / 100.0

        val buyOrders = mutableListOf<OrderItem>()
        val halfBudget = dailyBudget / 2.0

        if (currentT < totalDivisions / 2) {
            // First half: 0.5 unit star LOC, 0.5 unit average price LOC
            val qStar = if (starPrice > 0) (halfBudget / starPrice).toInt() else 0
            if (qStar > 0) {
                val rate = ((starPrice / currentPrice) - 1.0) * 100.0
                buyOrders.add(
                    OrderItem(
                        stage = "별지점 LOC 매수",
                        type = "LOC 매수",
                        price = starPrice,
                        shares = qStar,
                        changeRate = rate,
                        memo = "종가 ≤ $${String.format(Locale.US, "%.2f", starPrice)}"
                    )
                )
            }
            val avgP = if (account.averagePrice > 0) account.averagePrice else currentPrice
            val qAvg = if (avgP > 0) (halfBudget / avgP).toInt() else 0
            if (qAvg > 0) {
                val rate = ((avgP / currentPrice) - 1.0) * 100.0
                buyOrders.add(
                    OrderItem(
                        stage = "평단가 LOC 매수",
                        type = "LOC 매수",
                        price = avgP,
                        shares = qAvg,
                        changeRate = rate,
                        memo = "종가 ≤ $${String.format(Locale.US, "%.2f", avgP)}"
                    )
                )
            }
        } else {
            // Second half: 1 unit star LOC
            val q = if (starPrice > 0) (dailyBudget / starPrice).toInt() else 0
            if (q > 0) {
                val rate = ((starPrice / currentPrice) - 1.0) * 100.0
                buyOrders.add(
                    OrderItem(
                        stage = "후반전 별지점 LOC 매수",
                        type = "LOC 매수",
                        price = starPrice,
                        shares = q,
                        changeRate = rate,
                        memo = "종가 ≤ $${String.format(Locale.US, "%.2f", starPrice)}"
                    )
                )
            }
        }

        // Sell orders
        val sellOrders = mutableListOf<OrderItem>()
        if (account.totalShares > 0) {
            val targetGain = if (isSoxl) 0.20 else 0.15
            val targetPrice = ceil((account.averagePrice * (1.0 + targetGain)) * 100.0) / 100.0
            val targetRate = ((targetPrice / currentPrice) - 1.0) * 100.0
            sellOrders.add(
                OrderItem(
                    stage = "지정가 전량 익절",
                    type = "지정가 매도",
                    price = targetPrice,
                    shares = account.totalShares,
                    changeRate = targetRate,
                    memo = "지정가 $${String.format(Locale.US, "%.2f", targetPrice)}"
                )
            )
        }

        return JongJongEngine.OrderPlan(
            buyOrders = buyOrders,
            sellOrders = sellOrders,
            currentMode = "v4.0 (T=${currentT})",
            singleDivisionBudget = dailyBudget
        )
    }
}
