package com.swir.swirsms

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.text.DateFormat
import java.util.Date
import java.util.Locale

class Words(language: String) {
    private val polish = language=="pl" || (language=="system" && Locale.getDefault().language=="pl")
    fun t(pl: String, en: String) = if(polish) pl else en
    fun state(value: String): String = when(value) {
        "QUEUED" -> t("W kolejce", "Queued")
        "SENDING" -> t("Wysyłanie", "Sending")
        "SENT" -> t("Wysłano", "Sent")
        "DELIVERED" -> t("Dostarczono", "Delivered")
        "FAILED" -> t("Błąd wysyłki", "Send failed")
        "PARTIAL" -> t("Wysłano częściowo", "Partially sent")
        "DELIVERY_FAILED" -> t("Błąd dostarczenia", "Delivery failed")
        "UNKNOWN" -> t("Status niepewny", "Unconfirmed status")
        "CANCELLED" -> t("Anulowano", "Cancelled")
        "EXPIRED" -> t("Termin wygasł", "Expired")
        else -> value
    }
    fun detail(value: String): String = when(value) {
        "NO_SMS_PERMISSION", "PERMISSION_DENIED" -> t("Brak zgody na wysyłanie SMS. Sprawdź uprawnienia.","SMS permission missing. Check permissions.")
        "SIM_UNAVAILABLE" -> t("Wybrana SIM jest nieaktywna albo nie ma zgody na odczyt kart.","Selected SIM is inactive or SIM access permission is missing.")
        "OVER_24H" -> t("Opóźnienie przekroczyło 24 godziny. Nic nie wysłano.","Delayed by more than 24 hours. Nothing was sent.")
        "TRANSPORT_EXCEPTION", "NO_CALLBACK" -> t("Brak pewnego potwierdzenia. Nie ponowiono automatycznie; sprawdź u odbiorcy przed ponowną wysyłką.","No reliable confirmation. Not retried automatically; check with the recipient before resending.")
        "INVALID_ARGUMENT" -> t("Nieprawidłowy numer, treść lub zbyt wiele części.","Invalid number, message or too many segments.")
        "SCHEDULER_ERROR" -> t("Nie udało się uruchomić kolejki. Otwórz aplikację ponownie i sprawdź historię.","Could not start the queue. Reopen the app and check history.")
        "AUTH_UNAVAILABLE" -> t("Najpierw ustaw PIN, wzór, hasło lub biometrię blokady telefonu.","First set up a device screen lock (PIN, pattern, password or biometrics).")
        "MODEM_2" -> t("Radio telefonu jest wyłączone.","Phone radio is turned off.")
        "MODEM_4" -> t("Brak usługi sieci komórkowej.","No cellular service.")
        "" -> ""
        else -> t("Kod raportu Androida / sieci: ","Android / network report code: ")+value
    }
}
fun dateText(time: Long): String = DateFormat.getDateTimeInstance(DateFormat.MEDIUM,DateFormat.SHORT).format(Date(time))
val Ink = Color(0xFF080E19)
val Blue = Color(0xFF82C5FF)
val SwirColors = darkColorScheme(primary=Blue, onPrimary=Color(0xFF002E50), secondary=Color(0xFF91D9C5), background=Ink, surface=Color(0xFF111D2F), surfaceVariant=Color(0xFF213149), onSurface=Color(0xFFE5EDF8), onSurfaceVariant=Color(0xFFABBDD1), outline=Color(0xFF4B617B))
@Composable fun Panel(title: String, subtitle: String = "", content: @Composable ColumnScope.()->Unit) {
    Surface(shape=RoundedCornerShape(24.dp),color=MaterialTheme.colorScheme.surface,modifier=Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            Text(title,style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.SemiBold)
            if(subtitle.isNotEmpty()) Text(subtitle,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            content()
        }
    }
}
@Composable fun Hero(w: Words) {
    Column(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(Color(0xFF163959),Color(0xFF14243C),Color(0xFF111D2F))),RoundedCornerShape(24.dp)).padding(22.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(w.t("TWÓJ TELEFON. TWOJE WIADOMOŚCI.","YOUR PHONE. YOUR MESSAGES."),style=MaterialTheme.typography.labelSmall,color=Blue)
        Text(w.t("Prosto z Twojej SIM.","Straight from your SIM."),style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold)
        Text(w.t("Bez konta, internetu i serwera. Zwykłe SMS-y, pełna kontrola przed wysłaniem.","No account, internet or server. Standard SMS, with a review before every send."),style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
