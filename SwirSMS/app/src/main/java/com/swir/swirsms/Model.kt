package com.swir.swirsms

import java.util.UUID

data class Recipient(val name: String, val number: String)
data class SimChoice(val id: Int, val label: String)
data class Message(val id: String, val created: Long, val due: Long, val name: String, val number: String, val body: String, val sim: Int, val simLabel: String, val reports: Boolean, val state: String, val parts: Int, val detail: String, val token: String)
data class SavedItem(val id: String = UUID.randomUUID().toString(), val kind: String, val title: String, val body: String = "", val people: List<Recipient> = emptyList())
data class SmsStats(val encoding: String, val units: Int, val segments: Int)
object PhoneRules {
    fun normalize(raw: String): String? {
        val clean = raw.trim().replace(Regex("[\\s()\\-.]"), "")
        val value = if (clean.startsWith("00")) "+" + clean.drop(2) else clean
        return value.takeIf { Regex("\\+?[0-9]{7,15}").matches(it) }
    }
    fun unique(people: List<Recipient>): List<Recipient> = people.mapNotNull { p -> normalize(p.number)?.let { Recipient(p.name.trim().take(100), it) } }.distinctBy { it.number }
}
object SmsMath {
    private val basic = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ" + " !\"#¤%&'()*+,-./0123456789:;<=>?" + "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà").toSet()
    private val extended = "\u000c^{}\\[~]|€".toSet()
    fun stats(text: String): SmsStats {
        if (text.isEmpty()) return SmsStats("GSM-7", 0, 0)
        val gsm = text.all { it in basic || it in extended }
        val units: Int = if (gsm) text.fold(0) { n,c -> n + if(c in extended) 2 else 1 } else text.length
        val single = if (gsm) 160 else 70
        val multi = if (gsm) 153 else 67
        return SmsStats(if (gsm) "GSM-7" else "Unicode", units, if (units <= single) 1 else (units + multi - 1) / multi)
    }
}
object ResultRules {
    fun state(total: Int, sent: Int, failed: Int, delivered: Int, deliveryFailed: Int): String = when {
        failed > 0 && sent > 0 -> "PARTIAL"
        failed > 0 -> "FAILED"
        delivered == total && total > 0 -> "DELIVERED"
        deliveryFailed > 0 -> "DELIVERY_FAILED"
        sent == total && total > 0 -> "SENT"
        else -> "SENDING"
    }
    fun expired(due: Long, now: Long) = now - due > 86_400_000L
}
