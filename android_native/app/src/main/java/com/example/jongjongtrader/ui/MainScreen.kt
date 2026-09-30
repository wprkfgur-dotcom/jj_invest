package com.example.jongjongtrader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.model.Account
import com.example.jongjongtrader.data.repository.AccountRepository
import com.example.jongjongtrader.theme.*
import com.example.jongjongtrader.ui.screens.*

@Composable
fun MainAppContainer() {
    val context = LocalContext.current
    val repository = remember { AccountRepository(context) }
    val accounts by repository.accountsFlow.collectAsState()

    var selectedTabIndex by remember { mutableIntStateOf(0) }
    var selectedAccount by remember { mutableStateOf<Account?>(null) }

    Scaffold(
        bottomBar = {
            if (selectedAccount == null) {
                NavigationBar(
                    containerColor = SurfaceCard,
                    contentColor = TextPrimary,
                    tonalElevation = 8.dp
                ) {
                    NavigationBarItem(
                        selected = selectedTabIndex == 0,
                        onClick = { selectedTabIndex = 0 },
                        icon = { Icon(Icons.Default.Home, contentDescription = "홈") },
                        label = { Text("홈", fontSize = 11.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = AccentBlue,
                            selectedTextColor = AccentBlue,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextSecondary,
                            indicatorColor = AccentBlue.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTabIndex == 1,
                        onClick = { selectedTabIndex = 1 },
                        icon = { Icon(Icons.Default.AccountBalanceWallet, contentDescription = "계좌 현황") },
                        label = { Text("계좌 현황", fontSize = 11.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = AccentBlue,
                            selectedTextColor = AccentBlue,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextSecondary,
                            indicatorColor = AccentBlue.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTabIndex == 2,
                        onClick = { selectedTabIndex = 2 },
                        icon = { Icon(Icons.Default.Timeline, contentDescription = "백테스트") },
                        label = { Text("백테스트", fontSize = 11.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = AccentBlue,
                            selectedTextColor = AccentBlue,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextSecondary,
                            indicatorColor = AccentBlue.copy(alpha = 0.15f)
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTabIndex == 3,
                        onClick = { selectedTabIndex = 3 },
                        icon = { Icon(Icons.Default.Settings, contentDescription = "설정") },
                        label = { Text("설정", fontSize = 11.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = AccentBlue,
                            selectedTextColor = AccentBlue,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextSecondary,
                            indicatorColor = AccentBlue.copy(alpha = 0.15f)
                        )
                    )
                }
            }
        },
        containerColor = BgDark
    ) { innerPadding ->
        Box(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            if (selectedAccount != null) {
                AccountDetailScreen(
                    account = selectedAccount!!,
                    onBack = { selectedAccount = null },
                    onAccountUpdated = { updated ->
                        repository.saveAccount(updated)
                        selectedAccount = updated
                    }
                )
            } else {
                when (selectedTabIndex) {
                    0 -> HomeScreen(accounts = accounts)
                    1 -> AccountsScreen(
                        accounts = accounts,
                        onAccountClick = { acc -> selectedAccount = acc },
                        onAddAccount = { newAcc -> repository.saveAccount(newAcc) }
                    )
                    2 -> BacktestScreen()
                    3 -> SettingsScreen(repository = repository)
                }
            }
        }
    }
}
