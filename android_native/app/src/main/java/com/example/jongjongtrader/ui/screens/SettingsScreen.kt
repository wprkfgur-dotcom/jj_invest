package com.example.jongjongtrader.ui.screens

import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.jongjongtrader.data.repository.AccountRepository
import com.example.jongjongtrader.theme.*

@Composable
fun SettingsScreen(
    repository: AccountRepository
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDark)
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("설정 및 데이터 관리", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = SurfaceCard),
            shape = RoundedCornerShape(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("데이터 내보내기", color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text(
                    "운용 중인 모든 계좌의 거래 내역과 정산 기록을 엑셀과 호환되는 CSV 파일로 공유 및 내보내기합니다.",
                    color = TextSecondary,
                    fontSize = 12.sp
                )

                Button(
                    onClick = {
                        val csvData = repository.exportTransactionsCsv()
                        val sendIntent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_TEXT, csvData)
                            type = "text/csv"
                        }
                        val shareIntent = Intent.createChooser(sendIntent, "거래 내역 CSV 내보내기")
                        context.startActivity(shareIntent)
                        Toast.makeText(context, "CSV 내보내기가 시작되었습니다.", Toast.LENGTH_SHORT).show()
                    },
                    modifier = Modifier.fillMaxWidth().height(46.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentBlue),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text("거래 내역 CSV 내보내기", color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = SurfaceCard),
            shape = RoundedCornerShape(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BorderColor)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("애플리케이션 정보", color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("버전", color = TextSecondary, fontSize = 13.sp)
                    Text("1.0.0 Native (Compose)", color = TextPrimary, fontSize = 13.sp)
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("엔진", color = TextSecondary, fontSize = 13.sp)
                    Text("JongJong & Infinite v4.0", color = TextPrimary, fontSize = 13.sp)
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("아키텍처", color = TextSecondary, fontSize = 13.sp)
                    Text("Pure Kotlin / Material 3", color = AccentBlue, fontSize = 13.sp)
                }
            }
        }
    }
}
