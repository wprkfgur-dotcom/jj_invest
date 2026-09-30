package com.example.jongjongtrader.domain

import com.example.jongjongtrader.data.model.BacktestMetric
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.*

object BacktestEngine {

    data class Candle(
        val date: String,
        val close: Double
    )

    fun runBacktest(
        ticker: String,
        strategyName: String,
        initialSeed: Double,
        candles: List<Candle>
    ): BacktestMetric {
        if (candles.isEmpty()) {
            return BacktestMetric(
                stratName = strategyName,
                ticker = ticker,
                initialSeed = initialSeed,
                finalAsset = initialSeed,
                totalReturn = 0.0,
                cagr = 0.0,
                mdd = 0.0,
                winRate = 0.0,
                dates = emptyList(),
                stratAssets = emptyList(),
                bnhAssets = emptyList()
            )
        }

        val dates = mutableListOf<String>()
        val stratAssets = mutableListOf<Double>()
        val bnhAssets = mutableListOf<Double>()

        val firstPrice = candles.first().close
        var currentCash = initialSeed
        var currentShares = 0
        var peakAsset = initialSeed
        var maxDrawdown = 0.0
        var winCount = 0
        var tradeCount = 0

        val splitDivisions = if (strategyName.contains("무한매수")) 40.0 else 10.0
        val targetYield = if (strategyName.contains("무한매수")) 0.15 else 0.03
        var costBasis = 0.0

        for (candle in candles) {
            val p = candle.close
            val bnhVal = (initialSeed / firstPrice) * p
            bnhAssets.add(bnhVal)
            dates.add(candle.date)

            // Sell check
            if (currentShares > 0) {
                val avg = costBasis / currentShares
                if (p >= avg * (1.0 + targetYield)) {
                    val proceed = currentShares * p
                    val profit = proceed - costBasis
                    currentCash += proceed
                    if (profit > 0) winCount++
                    tradeCount++
                    currentShares = 0
                    costBasis = 0.0
                }
            }

            // Buy check
            val singleUnit = (initialSeed * 0.95) / splitDivisions
            if (currentCash >= singleUnit && p > 0) {
                val buyQty = (singleUnit / p).toInt()
                if (buyQty > 0) {
                    val cost = buyQty * p
                    currentCash -= cost
                    currentShares += buyQty
                    costBasis += cost
                }
            }

            val currentTot = currentCash + (currentShares * p)
            stratAssets.add(currentTot)

            if (currentTot > peakAsset) {
                peakAsset = currentTot
            } else {
                val dd = (peakAsset - currentTot) / peakAsset
                if (dd > maxDrawdown) maxDrawdown = dd
            }
        }

        val finalAsset = stratAssets.lastOrNull() ?: initialSeed
        val totalReturn = ((finalAsset - initialSeed) / initialSeed) * 100.0
        val years = max(0.1, candles.size / 252.0)
        val cagr = ((finalAsset / initialSeed).pow(1.0 / years) - 1.0) * 100.0
        val winRate = if (tradeCount > 0) (winCount.toDouble() / tradeCount) * 100.0 else 100.0

        return BacktestMetric(
            stratName = strategyName,
            ticker = ticker,
            initialSeed = initialSeed,
            finalAsset = finalAsset,
            totalReturn = totalReturn,
            cagr = cagr,
            mdd = maxDrawdown * 100.0,
            winRate = winRate,
            dates = dates,
            stratAssets = stratAssets,
            bnhAssets = bnhAssets
        )
    }

    fun generateSampleCandles(ticker: String, days: Int = 180): List<Candle> {
        val list = mutableListOf<Candle>()
        var price = when (ticker.uppercase()) {
            "SOXL" -> 38.5
            "TQQQ" -> 72.0
            "UPRO" -> 85.0
            else -> 50.0
        }

        val sdf = SimpleDateFormat("MM/dd", Locale.KOREA)
        val now = System.currentTimeMillis()
        val oneDay = 24L * 60 * 60 * 1000

        for (i in (days - 1) downTo 0) {
            val dStr = sdf.format(Date(now - i * oneDay))
            val drift = (Math.sin(i * 0.1) * 0.02) + (Math.random() - 0.48) * 0.05
            price = max(5.0, price * (1.0 + drift))
            list.add(Candle(dStr, floor(price * 100.0) / 100.0))
        }
        return list
    }
}
