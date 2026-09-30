package com.example.jongjongtrader.domain

import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.data.model.Lot
import com.example.jongjongtrader.data.model.OrderItem
import com.example.jongjongtrader.data.model.Transaction
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.*

object JongJongEngine {

    data class OrderPlan(
        val buyOrders: List<OrderItem>,
        val sellOrders: List<OrderItem>,
        val currentMode: String = "Normal",
        val singleDivisionBudget: Double = 0.0
    )

    fun calculateOrders(account: Account, currentPrice: Double): OrderPlan {
        if (currentPrice <= 0.0) {
            return OrderPlan(emptyList(), emptyList())
        }

        val activeSeed = account.activeSeed
        val splitRounds = 8.0 // default for Normal mode
        val singleBudget = if (splitRounds > 0) activeSeed / splitRounds else activeSeed / 8.0
        val effectiveBudget = min(singleBudget, max(0.0, account.currentCash))

        val buyOrders = mutableListOf<OrderItem>()
        val rangeNormal = 0.128 // 12.8%
        val splitCount = 5
        val curvature = 0.7

        val topBuyPrice = floor((currentPrice * (1.0 + rangeNormal) - 0.01) * 100.0) / 100.0
        val bottomBuyPrice = floor(currentPrice * (1.0 - rangeNormal) * 100.0) / 100.0

        val prices = mutableListOf<Double>()
        prices.add(topBuyPrice)

        val steps = splitCount - 1
        for (i in 0 until (steps - 1)) {
            val ratio = ((steps - 2.0 - i) / (steps - 2.0)).pow(curvature)
            val denom = bottomBuyPrice + ratio * (topBuyPrice - bottomBuyPrice)
            val p = floor(denom * 100.0) / 100.0
            if (p > 0) prices.add(p)
        }

        var prevQty = 0
        for ((idx, p) in prices.withIndex()) {
            if (p > 0 && effectiveBudget > 0) {
                val totalQty = (effectiveBudget / p).toInt()
                val deltaQty = if (idx == 0) totalQty else max(0, totalQty - prevQty)
                prevQty = totalQty
                if (deltaQty > 0) {
                    val rate = ((p / currentPrice) - 1.0) * 100.0
                    buyOrders.add(
                        OrderItem(
                            stage = "${idx + 1}차 매수",
                            type = "LOC 매수",
                            price = p,
                            shares = deltaQty,
                            changeRate = rate,
                            memo = "종가 ≤ $${String.format(Locale.US, "%.2f", p)}"
                        )
                    )
                }
            }
        }

        // Sell Orders
        val sellOrders = mutableListOf<OrderItem>()
        if (account.totalShares > 0) {
            val targetYield = account.targetProfitRate
            val targetPrice = ceil((account.averagePrice * (1.0 + targetYield)) * 100.0) / 100.0
            val rate = ((targetPrice / currentPrice) - 1.0) * 100.0
            sellOrders.add(
                OrderItem(
                    stage = "목표 익절 매도",
                    type = "LOC 매도",
                    price = targetPrice,
                    shares = account.totalShares,
                    changeRate = rate,
                    memo = "종가 ≥ $${String.format(Locale.US, "%.2f", targetPrice)}"
                )
            )
        }

        return OrderPlan(
            buyOrders = buyOrders,
            sellOrders = sellOrders,
            currentMode = "Normal",
            singleDivisionBudget = effectiveBudget
        )
    }

    fun executeDailySettlement(
        account: Account,
        closePrice: Double,
        executedBuyShares: Int,
        executedSellShares: Int,
        dateStr: String = SimpleDateFormat("yyyy-MM-dd", Locale.KOREA).format(Date())
    ): Account {
        var newCash = account.currentCash
        val newLots = account.lots.toMutableList()
        val newHistory = account.history.toMutableList()

        // 1. Sell execution
        if (executedSellShares > 0 && account.totalShares > 0) {
            val sellQty = min(executedSellShares, account.totalShares)
            val sellAmount = sellQty * closePrice
            newCash += sellAmount

            // FIFO remove lots
            var remainingToSell = sellQty
            var costBasis = 0.0
            while (remainingToSell > 0 && newLots.isNotEmpty()) {
                val lot = newLots.removeAt(0)
                if (lot.shares <= remainingToSell) {
                    remainingToSell -= lot.shares
                    costBasis += lot.shares * lot.buyPrice
                } else {
                    val keptShares = lot.shares - remainingToSell
                    costBasis += remainingToSell * lot.buyPrice
                    newLots.add(0, lot.copy(shares = keptShares, amount = keptShares * lot.buyPrice))
                    remainingToSell = 0
                }
            }
            val profit = sellAmount - costBasis
            val profitRate = if (costBasis > 0) (profit / costBasis) * 100.0 else 0.0

            newHistory.add(
                0,
                Transaction(
                    date = dateStr,
                    type = "매도",
                    price = closePrice,
                    shares = sellQty,
                    amount = sellAmount,
                    profit = profit,
                    profitRate = profitRate,
                    memo = "일일 정산 체결"
                )
            )
        }

        // 2. Buy execution
        if (executedBuyShares > 0) {
            val buyAmount = executedBuyShares * closePrice
            if (newCash >= buyAmount) {
                newCash -= buyAmount
                val nextIndex = (newLots.maxOfOrNull { it.index } ?: 0) + 1
                newLots.add(
                    Lot(
                        index = nextIndex,
                        buyPrice = closePrice,
                        shares = executedBuyShares,
                        buyDate = dateStr,
                        amount = buyAmount
                    )
                )
                newHistory.add(
                    0,
                    Transaction(
                        date = dateStr,
                        type = "매수",
                        price = closePrice,
                        shares = executedBuyShares,
                        amount = buyAmount,
                        memo = "일일 정산 체결 (${nextIndex}회차 조각)"
                    )
                )
            }
        }

        return account.copy(
            currentCash = newCash,
            lots = newLots,
            history = newHistory
        )
    }
}
