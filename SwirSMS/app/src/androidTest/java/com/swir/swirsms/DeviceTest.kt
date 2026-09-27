package com.swir.swirsms

import android.content.pm.PackageManager
import android.graphics.Bitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class DeviceTest {
 @get:Rule val compose=createAndroidComposeRule<MainActivity>()
 private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
 @Suppress("DEPRECATION")
 @Test fun noInternetOrAddressBookPermission() {
   val requested=context.packageManager.getPackageInfo(context.packageName,PackageManager.GET_PERMISSIONS).requestedPermissions.orEmpty()
   assertFalse(requested.contains("android.permission.INTERNET"))
   assertFalse(requested.contains("android.permission.READ_CONTACTS"))
   assertFalse(requested.contains("android.permission.READ_SMS"))
   assertTrue(requested.contains("android.permission.SEND_SMS"))
 }
 @Test fun allTabsOpenAndCapture() {
   val names=listOf("composer","history","library","settings")
   val dir=File(context.getExternalFilesDir(null),"screenshots").apply {mkdirs()}
   names.forEachIndexed { i,name ->
     compose.onNodeWithTag("nav-$i").performClick()
     compose.onNodeWithTag(name).assertExists()
     compose.waitForIdle()
     val shot=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
     File(dir,"$name.png").outputStream().use { shot.compress(Bitmap.CompressFormat.PNG,100,it) }
     shot.recycle()
   }
 }
 @Test fun draftPersistsLocally() {
   val field=compose.onNodeWithTag("message-body")
   field.performScrollTo()
   field.performTextClearance()
   field.performTextInput("SwirSMS draft check")
   compose.waitForIdle()
   assertEquals("SwirSMS draft check",LocalPrefs(context).draft)
   field.performTextClearance()
 }
 @Test fun invalidSendDoesNotCreateMessages() {
   val before=SmsDb.get(context).messages().size
   compose.onNodeWithTag("message-body").performScrollTo().performTextClearance()
   compose.onNodeWithTag("send-button").performScrollTo().performClick()
   compose.onNodeWithText("OK").assertExists().performClick()
   assertEquals(before,SmsDb.get(context).messages().size)
 }
 @Test fun duplicateClaimIsBlockedAndCancelledCannotSend() {
   val db=SmsDb.get(context); val due=System.currentTimeMillis()+86_000_000
   val id=db.addBatch(listOf(Recipient("emulator fixture","15555215554")),"test only",SimChoice(0,"TEST"),due,true).single()
   try {
     assertNull(db.claim(id,System.currentTimeMillis()))
     assertTrue(db.cancel(id))
     assertNull(db.claim(id,due+1))
   } finally {db.cancel(id);db.delete(id)}
 }
 @Test fun multipartReportsAreIdempotentAndTokenChecked() {
   val db=SmsDb.get(context);val due=System.currentTimeMillis()+86_000_000
   val id=db.addBatch(listOf(Recipient("emulator fixture","15555215554")),"test only",SimChoice(0,"TEST"),due,true).single()
   try {
     val msg=db.claim(id,due)!!
     assertNull(db.claim(id,due))
     db.prepareParts(id,2)
     db.record(id,"wrong",0,false,1)
     assertEquals("SENDING",db.getMessage(id)!!.state)
     db.record(id,msg.token,0,false,1);db.record(id,msg.token,0,false,1)
     assertEquals("SENDING",db.getMessage(id)!!.state)
     db.record(id,msg.token,1,false,1)
     assertEquals("SENT",db.getMessage(id)!!.state)
     db.record(id,msg.token,0,true,1)
     assertEquals("SENT",db.getMessage(id)!!.state)
     db.record(id,msg.token,1,true,1)
     assertEquals("DELIVERED",db.getMessage(id)!!.state)
   } finally { db.cancel(id);db.delete(id) }
 }
 @Test fun libraryRoundTrip() {
   val db=SmsDb.get(context)
   val group=SavedItem(kind="GROUP",title="Test group",people=listOf(Recipient("emulator fixture","15555215554")))
   try { db.save(group); assertEquals(group,db.saved().first {it.id==group.id}) }
   finally {db.deleteSaved(group.id)}
 }
}
