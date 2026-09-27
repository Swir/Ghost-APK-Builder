package com.swir.swirsms

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.work.WorkManager
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class CallbackTest {
 private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
 @Test fun manifestReceiverRecordsRealAndroidBroadcastWithoutSendingSms() {
   val db=SmsDb.get(context); val due=System.currentTimeMillis()+86_000_000
   val id=db.addBatch(listOf(Recipient("emulator fixture","15555215554")),"local callback fixture",SimChoice(0,"TEST"),due,true).single()
   try {
     val msg=db.claim(id,due)!!; db.prepareParts(id,1)
     val latch=CountDownLatch(1)
     val intent=Intent(context,SmsStatusReceiver::class.java).apply {
       action="com.swir.swirsms.SENT";data=Uri.parse("swirsms://test/$id")
       putExtra("id",id);putExtra("token",msg.token);putExtra("part",0)
     }
     context.sendOrderedBroadcast(intent,null,object:BroadcastReceiver() {override fun onReceive(c:Context,i:Intent) {latch.countDown()}},null,Activity.RESULT_OK,null,null)
     assertTrue(latch.await(10,TimeUnit.SECONDS))
     assertEquals("SENT",db.getMessage(id)!!.state)
   } finally {db.cancel(id);db.delete(id)}
 }
 @Test fun futureWorkCanBePersistedAndCancelledWithoutTransport() {
   val db=SmsDb.get(context);val due=System.currentTimeMillis()+86_000_000
   val id=db.addBatch(listOf(Recipient("emulator fixture","15555215554")),"future fixture",SimChoice(0,"TEST"),due,true).single()
   try {
     SmsQueue.enqueue(context,id,due)
     assertTrue(WorkManager.getInstance(context).getWorkInfosForUniqueWork("sms-$id").get(10,TimeUnit.SECONDS).isNotEmpty())
     assertTrue(SmsQueue.cancel(context,id))
     assertEquals("CANCELLED",db.getMessage(id)!!.state)
   } finally {SmsQueue.cancel(context,id);db.delete(id)}
 }
}
