package com.example.jongjongtrader.data.model

import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class Lot(
    val index: Int,
    val buyPrice: Double,
    val shares: Int,
    val buyDate: String = "",
    val amount: Double = buyPrice * shares
)

@Serializable
data class Transaction(
    val id: String = UUID.randomUUID().toString(),
    val date: String,
    val type: String, // "매수", "매도", "정산"
    val price: Double,
    val shares: Int,
    val amount: Double = price * shares,
    val profit: Double = 0.0,
    val profitRate: Double = 0.0,
    val memo: String = ""
)

@Serializable
data class OrderItem(
    val stage: String,    // "1차 매수", "목표 익절 매도"
    val type: String,     // "LOC 매수", "LOC 매도"
    val price: Double,
    val shares: Int,
    val changeRate: Double, // e.g. -3.0%, +3.5%
    val memo: String = ""
)

@Serializable
data class Account(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val strategy: String = "종종전략", // "종종전략", "무한매수 v4", "단순보유"
    val ticker: String = "SOXL",
    val totalSeed: Double = 10000.0,
    val crisisReserveRatio: Double = 0.05, // 5%
    val targetProfitRate: Double = 0.03, // 3%
    val currentCash: Double = 9500.0,
    val lots: List<Lot> = emptyList(),
    val history: List<Transaction> = emptyList(),
    val createdAt: Long = System.currentTimeMillis()
) {
    val crisisReserve: Double
        get() = totalSeed * crisisReserveRatio

    val activeSeed: Double
        get() = totalSeed * (1.0 - crisisReserveRatio)

    val totalShares: Int
        get() = lots.sumOf { it.shares }

    val totalInvested: Double
        get() = lots.sumOf { it.amount }

    val averagePrice: Double
        get() = if (totalShares > 0) totalInvested / totalShares else 0.0

    fun calculateTotalAsset(currentPrice: Double): Double {
        return currentCash + (totalShares * currentPrice)
    }

    fun calculateProfit(currentPrice: Double): Double {
        return (totalShares * currentPrice) - totalInvested
    }

    fun calculateProfitRate(currentPrice: Double): Double {
        return if (totalInvested > 0) (calculateProfit(currentPrice) / totalInvested) * 100.0 else 0.0
    }
}

data class BacktestMetric(
    val stratName: String,
    val ticker: String,
    val initialSeed: Double,
    val finalAsset: Double,
    val totalReturn: Double,
    val cagr: Double,
    val mdd: Double,
    val winRate: Double,
    val dates: List<String>,
    val stratAssets: List<Double>,
    val bnhAssets: List<Double>
)
