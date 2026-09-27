package com.swir.swirsms

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.telephony.SmsManager
import android.telephony.SmsMessage
import android.telephony.SubscriptionManager
import androidx.work.*
import java.util.concurrent.TimeUnit

object Sims {
    fun permission(context: Context, permission: String) = context.checkSelfPermission(permission)==PackageManager.PERMISSION_GRANTED
    fun hasSms(context: Context) = context.packageManager.hasSystemFeature(PackageManager.FEATURE_TELEPHONY) || context.packageManager.hasSystemFeature("android.hardware.telephony.messaging")
    @SuppressLint("MissingPermission")
    fun list(context: Context): List<SimChoice> {
        if(!permission(context,Manifest.permission.READ_PHONE_STATE)) return emptyList()
        return runCatching { context.getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList.orEmpty().sortedBy { it.simSlotIndex }.map { SimChoice(it.subscriptionId,"SIM ${it.simSlotIndex+1} · ${it.displayName}") } }.getOrDefault(emptyList())
    }
    @Suppress("DEPRECATION")
    fun manager(context: Context, id: Int): SmsManager = if(Build.VERSION.SDK_INT>=31) context.getSystemService(SmsManager::class.java).createForSubscriptionId(id) else SmsManager.getSmsManagerForSubscriptionId(id)
}

object SmsQueue {
    fun enqueue(context: Context, id: String, due: Long) {
        val job = OneTimeWorkRequestBuilder<SendSmsWorker>().setInputData(workDataOf("id" to id)).setInitialDelay((due-System.currentTimeMillis()).coerceAtLeast(0),TimeUnit.MILLISECONDS).addTag("swirsms-outbox").build()
        WorkManager.getInstance(context).enqueueUniqueWork("sms-$id",ExistingWorkPolicy.KEEP,job)
    }
    fun recover(context: Context) { SmsDb.get(context).pending().forEach { enqueue(context,it.id,it.due) }; SmsDb.get(context).markUncertain() }
    fun cancel(context: Context, id: String): Boolean {
        if(!SmsDb.get(context).cancel(id)) return false
        WorkManager.getInstance(context).cancelUniqueWork("sms-$id"); return true
    }
}

class SendSmsWorker(context: Context, params: WorkerParameters): Worker(context,params) {
    @SuppressLint("MissingPermission")
    override fun doWork(): Result {
        val db = SmsDb.get(applicationContext)
        val id = inputData.getString("id") ?: return Result.failure()
        val before = db.getMessage(id) ?: return Result.success()
        if(before.state!="QUEUED") return Result.success() // Never resubmit an uncertain send after process death.
        val now = System.currentTimeMillis()
        if(now<before.due) return Result.retry()
        val msg = db.claim(id,now) ?: return Result.success()
        if(ResultRules.expired(msg.due,now)) { db.mark(id,"EXPIRED","OVER_24H"); return Result.success() }
        if(!Sims.hasSms(applicationContext) || !Sims.permission(applicationContext,Manifest.permission.SEND_SMS)) { db.mark(id,"FAILED","NO_SMS_PERMISSION"); return Result.success() }
        if(Sims.list(applicationContext).none { it.id==msg.sim }) { db.mark(id,"FAILED","SIM_UNAVAILABLE"); return Result.success() }
        try {
            val manager = Sims.manager(applicationContext,msg.sim)
            val parts = manager.divideMessage(msg.body)
            require(parts.size in 1..10)
            db.prepareParts(id,parts.size)
            val sent = ArrayList<PendingIntent>()
            val delivered = if(msg.reports) ArrayList<PendingIntent>() else null
            parts.indices.forEach { i ->
                sent.add(callback(msg,i,false))
                delivered?.add(callback(msg,i,true))
            }
            if(parts.size==1) manager.sendTextMessage(msg.number,null,msg.body,sent[0],delivered?.get(0))
            else manager.sendMultipartTextMessage(msg.number,null,parts,sent,delivered)
        } catch(e: SecurityException) { db.mark(id,"FAILED","PERMISSION_DENIED") }
          catch(e: IllegalArgumentException) { db.mark(id,"FAILED","INVALID_ARGUMENT") }
          catch(e: Exception) { db.mark(id,"UNKNOWN","TRANSPORT_EXCEPTION") }
        // System callbacks, not this return value, determine SENT / DELIVERED.
        return Result.success()
    }
    private fun callback(msg: Message, part: Int, delivered: Boolean): PendingIntent {
        val intent = Intent(applicationContext,SmsStatusReceiver::class.java).apply {
            action=if(delivered) "com.swir.swirsms.DELIVERY" else "com.swir.swirsms.SENT"
            data=Uri.parse("swirsms://status/${msg.id}/${if(delivered) "d" else "s"}/$part")
            putExtra("id",msg.id); putExtra("part",part); putExtra("token",msg.token)
        }
        // The delivery intent must accept the telephony service's status-report PDU.
        val mutability = if(delivered && Build.VERSION.SDK_INT>=31) PendingIntent.FLAG_MUTABLE else if(delivered) 0 else PendingIntent.FLAG_IMMUTABLE
        return PendingIntent.getBroadcast(applicationContext,0,intent,PendingIntent.FLAG_UPDATE_CURRENT or mutability)
    }
}

class SmsStatusReceiver: BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id=intent.getStringExtra("id") ?: return
        val token=intent.getStringExtra("token") ?: return
        val part=intent.getIntExtra("part",-1)
        val delivered=intent.action=="com.swir.swirsms.DELIVERY"
        if(!delivered && intent.action!="com.swir.swirsms.SENT") return
        val result=resultCode
        val db=SmsDb.get(context)
        if(!delivered) {
            db.record(id,token,part,false,if(result==Activity.RESULT_OK) 1 else -1,if(result==Activity.RESULT_OK) "" else "MODEM_$result")
        } else {
            val status=runCatching { intent.getByteArrayExtra("pdu")?.let { SmsMessage.createFromPdu(it,intent.getStringExtra("format") ?: "3gpp")?.status } }.getOrNull()
            when {
                status!=null && status in 0..31 -> db.record(id,token,part,true,1)
                status!=null && status in 64..127 -> db.record(id,token,part,true,-1,"DELIVERY_$status")
                result!=Activity.RESULT_OK -> db.record(id,token,part,true,-1,"DELIVERY_RESULT_$result")
                // Missing/temporary status report is not proof of delivery.
            }
        }
    }
}
