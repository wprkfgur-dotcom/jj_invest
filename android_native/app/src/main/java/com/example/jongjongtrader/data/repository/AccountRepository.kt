package com.example.jongjongtrader.data.repository

import android.content.Context
import com.example.jongjongtrader.data.model.Account
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.File

class AccountRepository(private val context: Context) {

    private val json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
    }

    private val file = File(context.filesDir, "accounts.json")
    private val _accountsFlow = MutableStateFlow<List<Account>>(emptyList())
    val accountsFlow: StateFlow<List<Account>> = _accountsFlow.asStateFlow()

    init {
        loadAccounts()
    }

    private fun loadAccounts() {
        if (!file.exists()) {
            file.writeText("[]")
            _accountsFlow.value = emptyList()
            return
        }
        try {
            val content = file.readText()
            val list = json.decodeFromString<List<Account>>(content)
            _accountsFlow.value = list
        } catch (e: Exception) {
            _accountsFlow.value = emptyList()
        }
    }

    fun saveAccount(account: Account) {
        val current = _accountsFlow.value.toMutableList()
        val index = current.indexOfFirst { it.id == account.id }
        if (index >= 0) {
            current[index] = account
        } else {
            current.add(account)
        }
        persist(current)
    }

    fun deleteAccount(accountId: String) {
        val current = _accountsFlow.value.filter { it.id != accountId }
        persist(current)
    }

    private fun persist(list: List<Account>) {
        _accountsFlow.value = list
        try {
            file.writeText(json.encodeToString(list))
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun exportTransactionsCsv(): String {
        val sb = StringBuilder()
        sb.append("계좌명,티커,일자,구분,단가($),수량(주),총금액($),실현손익($),메모\n")
        for (acc in _accountsFlow.value) {
            for (tx in acc.history) {
                sb.append("\"${acc.name}\",")
                sb.append("${acc.ticker},")
                sb.append("${tx.date},")
                sb.append("${tx.type},")
                sb.append("${String.format("%.2f", tx.price)},")
                sb.append("${tx.shares},")
                sb.append("${String.format("%.2f", tx.amount)},")
                sb.append("${String.format("%.2f", tx.profit)},")
                sb.append("\"${tx.memo}\"\n")
            }
        }
        return sb.toString()
    }
}
