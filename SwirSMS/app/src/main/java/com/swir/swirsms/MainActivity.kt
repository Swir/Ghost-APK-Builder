package com.swir.swirsms

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity: FragmentActivity() {
    var unlocked by mutableStateOf(false)
    private var authenticating=false
    private val prefs by lazy { LocalPrefs(this) }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        updateScreenProtection()
        unlocked=!prefs.lock
        setContent { SwirSmsApp(this) }
        lifecycleScope.launch(Dispatchers.IO) { SmsQueue.recover(applicationContext) }
    }
    fun updateScreenProtection() {
        if(prefs.lock) window.addFlags(WindowManager.LayoutParams.FLAG_SECURE) else window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
    }
    override fun onStop() { super.onStop(); if(prefs.lock) unlocked=false }
    override fun onStart() { super.onStart(); if(!prefs.lock) unlocked=true }
    fun authenticate(title: String, done: (Boolean,String)->Unit) {
        if(authenticating) return
        val allowed=BiometricManager.Authenticators.BIOMETRIC_WEAK or BiometricManager.Authenticators.DEVICE_CREDENTIAL
        if(BiometricManager.from(this).canAuthenticate(allowed)!=BiometricManager.BIOMETRIC_SUCCESS) { done(false,"AUTH_UNAVAILABLE"); return }
        authenticating=true
        val prompt=BiometricPrompt(this,ContextCompat.getMainExecutor(this),object: BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) { authenticating=false; unlocked=true; done(true,"") }
            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) { authenticating=false; done(false,errString.toString()) }
        })
        prompt.authenticate(BiometricPrompt.PromptInfo.Builder().setTitle(title).setAllowedAuthenticators(allowed).build())
    }
}
