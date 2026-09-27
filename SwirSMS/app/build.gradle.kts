plugins { id("com.android.application"); id("org.jetbrains.kotlin.plugin.compose") }
android {
    namespace = "com.swir.swirsms"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.swir.swirsms.standalone"
        minSdk = 26
        targetSdk = 36
        versionCode = 3
        versionName = "0.3.0-beta.2"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
    lint { abortOnError = true; checkReleaseBuilds = true }
}
dependencies {
    val bom = platform("androidx.compose:compose-bom:2025.08.00")
    implementation(bom); androidTestImplementation(bom)
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.fragment:fragment-ktx:1.8.9")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.9.4")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.work:work-runtime-ktx:2.10.3")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
