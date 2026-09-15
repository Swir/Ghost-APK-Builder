from __future__ import annotations

import re
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw

from . import AGP_VERSION, ANDROID_API
from .model import ProjectConfig

DEFAULT_MAIN = '''import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val title = TextView(this).apply {
            text = "Ghost APK Builder v17"
            textSize = 28f
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.rgb(8, 11, 18))
        }
        setContentView(title)
    }
}
'''


def kotlin_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def normalize_kotlin_source(source: str, package_name: str) -> str:
    source = source.strip() or DEFAULT_MAIN.strip()
    source = re.sub(r"^\s*package\s+[A-Za-z0-9_.]+\s*\n", "", source, count=1, flags=re.MULTILINE)
    return f"package {package_name}\n\n{source.rstrip()}\n"


class AndroidProjectGenerator:
    def generate(self, root: Path, cfg: ProjectConfig) -> Path:
        errors = cfg.validate()
        if errors:
            raise ValueError("\n".join(errors))
        if root.exists():
            shutil.rmtree(root)

        app = root / "app"
        main = app / "src" / "main"
        kotlin_dir = main / "java" / Path(*cfg.package_name.split("."))
        values = main / "res" / "values"
        drawable = main / "res" / "drawable"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        values.mkdir(parents=True, exist_ok=True)
        drawable.mkdir(parents=True, exist_ok=True)

        (root / "settings.gradle.kts").write_text(self._settings(), encoding="utf-8")
        (root / "build.gradle.kts").write_text(self._root_gradle(), encoding="utf-8")
        (root / "gradle.properties").write_text(
            "org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\n"
            "android.useAndroidX=true\n"
            "android.nonTransitiveRClass=true\n",
            encoding="utf-8",
        )
        (app / "build.gradle.kts").write_text(self._app_gradle(cfg), encoding="utf-8")
        (app / "proguard-rules.pro").write_text("# Ghost APK Builder generated rules\n", encoding="utf-8")
        (main / "AndroidManifest.xml").write_text(self._manifest(cfg), encoding="utf-8")
        (values / "strings.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            f'    <string name="app_name">{escape(cfg.app_name.strip())}</string>\n'
            "</resources>\n",
            encoding="utf-8",
        )
        (values / "colors.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            f'    <color name="ghost_status">{cfg.status_bar_color}</color>\n'
            f'    <color name="ghost_splash">{cfg.splash_background}</color>\n'
            "</resources>\n",
            encoding="utf-8",
        )
        (values / "themes.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            '    <style name="Theme.Ghost" parent="Theme.AppCompat.DayNight.NoActionBar">\n'
            '        <item name="android:fontFamily">sans</item>\n'
            '        <item name="android:windowLightStatusBar">false</item>\n'
            '        <item name="android:colorAccent">#00E5C3</item>\n'
            '        <item name="android:statusBarColor">@color/ghost_status</item>\n'
            '    </style>\n'
            "</resources>\n",
            encoding="utf-8",
        )
        (drawable / "ghost_background.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">\n'
            '    <solid android:color="@color/ghost_splash"/>\n'
            '</shape>\n',
            encoding="utf-8",
        )

        self._generate_icons(main / "res", cfg.icon_path)
        main_source = normalize_kotlin_source(cfg.custom_source, cfg.package_name)
        main_source = self._inject_runtime_setup(main_source, cfg)
        (kotlin_dir / "MainActivity.kt").write_text(main_source, encoding="utf-8")
        if self._runtime_permissions(cfg):
            (kotlin_dir / "GhostPermissions.kt").write_text(self._permissions_helper(cfg), encoding="utf-8")
        if cfg.use_splash:
            (kotlin_dir / "SplashActivity.kt").write_text(self._splash(cfg), encoding="utf-8")
        if cfg.extra_assets:
            shutil.copytree(Path(cfg.extra_assets), main / "assets", dirs_exist_ok=True)
        return root

    @staticmethod
    def _runtime_permissions(cfg: ProjectConfig) -> list[str]:
        permissions: list[str] = []
        if cfg.permission_camera:
            permissions.append("android.Manifest.permission.CAMERA")
        if cfg.permission_location:
            permissions.extend([
                "android.Manifest.permission.ACCESS_FINE_LOCATION",
                "android.Manifest.permission.ACCESS_COARSE_LOCATION",
            ])
        if cfg.permission_microphone:
            permissions.append("android.Manifest.permission.RECORD_AUDIO")
        return permissions

    @classmethod
    def _inject_runtime_setup(cls, source: str, cfg: ProjectConfig) -> str:
        setup: list[str] = [f'window.statusBarColor = android.graphics.Color.parseColor("{cfg.status_bar_color}")']
        if cfg.fullscreen:
            setup.append("window.decorView.systemUiVisibility = 5894")
        if cls._runtime_permissions(cfg):
            setup.append("GhostPermissions.requestMissing(this)")
        if "super.onCreate(" not in source:
            return source
        block = "\n        " + "\n        ".join(setup)
        return re.sub(r"(super\.onCreate\([^\n]*\))", r"\1" + block, source, count=1)

    @classmethod
    def _permissions_helper(cls, cfg: ProjectConfig) -> str:
        entries = ",\n        ".join(cls._runtime_permissions(cfg))
        return f'''package {cfg.package_name}

import android.app.Activity
import android.content.pm.PackageManager

object GhostPermissions {{
    private const val REQUEST_CODE = 1701
    private val REQUIRED = arrayOf(
        {entries}
    )

    fun requestMissing(activity: Activity) {{
        val missing = REQUIRED.filter {{ activity.checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }}
        if (missing.isNotEmpty()) {{
            activity.requestPermissions(missing.toTypedArray(), REQUEST_CODE)
        }}
    }}
}}
'''

    @staticmethod
    def _generate_icons(res_dir: Path, icon_path: str = "") -> None:
        canvas_size = 512
        if icon_path:
            source = Image.open(icon_path).convert("RGBA")
            side = min(source.size)
            left = (source.width - side) // 2
            top = (source.height - side) // 2
            source = source.crop((left, top, left + side, top + side)).resize(
                (canvas_size, canvas_size), Image.Resampling.LANCZOS
            )
        else:
            source = Image.new("RGBA", (canvas_size, canvas_size), "#071018")
            draw = ImageDraw.Draw(source)
            draw.rounded_rectangle((46, 46, 466, 466), radius=110, fill="#0E1925", outline="#00E5C3", width=22)
            draw.ellipse((135, 130, 377, 372), outline="#00E5C3", width=42)
            draw.rectangle((270, 238, 405, 285), fill="#0E1925")
            draw.rectangle((270, 238, 405, 285), outline="#00E5C3", width=18)

        sizes = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
        for density, size in sizes.items():
            folder = res_dir / f"mipmap-{density}"
            folder.mkdir(parents=True, exist_ok=True)
            icon = source.resize((size, size), Image.Resampling.LANCZOS)
            icon.save(folder / "ic_launcher.png")
            icon.save(folder / "ic_launcher_round.png")
            icon.save(folder / "ic_launcher_foreground.png")

        values = res_dir / "values"
        values.mkdir(parents=True, exist_ok=True)
        (values / "ghost_icon_colors.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            '    <color name="ghost_icon_background">#071018</color>\n'
            '</resources>\n',
            encoding="utf-8",
        )
        adaptive = res_dir / "mipmap-anydpi-v26"
        adaptive.mkdir(parents=True, exist_ok=True)
        xml = '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ghost_icon_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
'''
        (adaptive / "ic_launcher.xml").write_text(xml, encoding="utf-8")
        (adaptive / "ic_launcher_round.xml").write_text(xml, encoding="utf-8")

    @staticmethod
    def _settings() -> str:
        return '''pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "GhostGeneratedApp"
include(":app")
'''

    @staticmethod
    def _root_gradle() -> str:
        return f'''plugins {{
    id("com.android.application") version "{AGP_VERSION}" apply false
}}
'''

    @staticmethod
    def _app_gradle(cfg: ProjectConfig) -> str:
        minify = "true" if cfg.minify_release else "false"
        return f'''plugins {{
    id("com.android.application")
}}

val ghostStoreFile = System.getenv("GHOST_STORE_FILE")
val ghostStorePassword = System.getenv("GHOST_STORE_PASSWORD")
val ghostKeyAlias = System.getenv("GHOST_KEY_ALIAS")
val ghostKeyPassword = System.getenv("GHOST_KEY_PASSWORD")

android {{
    namespace = "{cfg.package_name}"
    compileSdk = {ANDROID_API}

    defaultConfig {{
        applicationId = "{cfg.package_name}"
        minSdk = {cfg.min_sdk}
        targetSdk = {max(ANDROID_API, cfg.target_sdk)}
        versionCode = {cfg.version_code}
        versionName = "{kotlin_string(cfg.version_name)}"
    }}

    if (ghostStoreFile != null && ghostStorePassword != null && ghostKeyAlias != null && ghostKeyPassword != null) {{
        signingConfigs {{
            create("ghostRelease") {{
                storeFile = file(ghostStoreFile)
                storePassword = ghostStorePassword
                keyAlias = ghostKeyAlias
                keyPassword = ghostKeyPassword
            }}
        }}
    }}

    buildTypes {{
        getByName("debug") {{ isMinifyEnabled = false }}
        getByName("release") {{
            isMinifyEnabled = {minify}
            isShrinkResources = {minify}
            signingConfig = signingConfigs.findByName("ghostRelease")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }}
    }}

    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}
}}

dependencies {{
    implementation("androidx.appcompat:appcompat:1.7.1")
}}
'''

    @staticmethod
    def _manifest(cfg: ProjectConfig) -> str:
        permissions = []
        if cfg.permission_internet:
            permissions.append("android.permission.INTERNET")
        if cfg.permission_camera:
            permissions.append("android.permission.CAMERA")
        if cfg.permission_location:
            permissions.extend(["android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION"])
        if cfg.permission_microphone:
            permissions.append("android.permission.RECORD_AUDIO")
        perm_xml = "\n".join(f'    <uses-permission android:name="{p}" />' for p in permissions)
        orientation = "" if cfg.orientation == "unspecified" else f' android:screenOrientation="{cfg.orientation}"'
        cleartext = "true" if cfg.allow_cleartext else "false"
        backup = "true" if cfg.allow_backup else "false"
        accel = "true" if cfg.hardware_accel else "false"
        launcher = ".SplashActivity" if cfg.use_splash else ".MainActivity"
        extra_main = '        <activity android:name=".MainActivity" android:exported="false" />\n' if cfg.use_splash else ""
        return f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
{perm_xml}
    <application
        android:allowBackup="{backup}"
        android:hardwareAccelerated="{accel}"
        android:usesCleartextTraffic="{cleartext}"
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:theme="@style/Theme.Ghost">
        <activity android:name="{launcher}" android:exported="true"{orientation}>
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
{extra_main}    </application>
</manifest>
'''

    @staticmethod
    def _splash(cfg: ProjectConfig) -> str:
        fullscreen = "window.decorView.systemUiVisibility = 5894" if cfg.fullscreen else ""
        return f'''package {cfg.package_name}

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class SplashActivity : AppCompatActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        {fullscreen}
        window.statusBarColor = Color.parseColor("{cfg.status_bar_color}")
        val container = LinearLayout(this).apply {{
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.parseColor("{cfg.splash_background}"))
        }}
        val icon = ImageView(this).apply {{
            setImageResource(R.mipmap.ic_launcher)
            layoutParams = LinearLayout.LayoutParams(260, 260).apply {{ bottomMargin = 28 }}
            alpha = 0f
            animate().alpha(1f).scaleX(1.04f).scaleY(1.04f).setDuration(500).start()
        }}
        val title = TextView(this).apply {{
            text = "{kotlin_string(cfg.app_name)}"
            textSize = 30f
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            alpha = 0f
            animate().alpha(1f).setDuration(650).start()
        }}
        container.addView(icon)
        container.addView(title)
        setContentView(container)
        Handler(Looper.getMainLooper()).postDelayed({{
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }}, 1200)
    }}
}}
'''
