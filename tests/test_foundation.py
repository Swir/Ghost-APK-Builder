import json, tempfile, unittest
from unittest import mock
from pathlib import Path
from ghost_builder import ANDROID_API, AGP_VERSION, BUILD_TOOLS, GRADLE_VERSION, VERSION
from ghost_builder.build_history import BuildHistoryStore
from ghost_builder.builder import GhostBuilder
from ghost_builder.certificates import parse_keytool_fingerprints
from ghost_builder.core import ConfigStore, Paths, ToolchainManager
from ghost_builder.generator import AndroidProjectGenerator, normalize_kotlin_source
from ghost_builder.i18n import STRINGS, Translator, normalize_language
from ghost_builder.model import ProjectConfig
from ghost_builder.project_store import RecentProjects, load_project, save_project
from ghost_builder.readiness import check_play_readiness
class FoundationTests(unittest.TestCase):
    def test_version_profile(self):self.assertEqual(VERSION,"17.0.0-beta.1");self.assertEqual(ANDROID_API,36);self.assertEqual(BUILD_TOOLS,"36.0.0");self.assertEqual(GRADLE_VERSION,"9.6.0");self.assertEqual(AGP_VERSION,"9.4.0")
    def test_config_never_persists_passwords(self):
        with tempfile.TemporaryDirectory() as td:
            store=ConfigStore(Path(td)/"config.json");store.save({"app_name":"Safe","store_password":"secret1","key_password":"secret2","keystore_pass":"legacy1","key_pass":"legacy2"});raw=json.loads((Path(td)/"config.json").read_text(encoding="utf-8"));self.assertEqual(raw["app_name"],"Safe")
            for key in ConfigStore.SECRET_KEYS:self.assertNotIn(key,raw)
    def test_language_policy_polish_or_english_fallback(self):self.assertEqual(normalize_language("pl_PL"),"pl");self.assertEqual(normalize_language("pl-PL"),"pl");self.assertEqual(normalize_language("de_DE"),"en");self.assertIn("projekt",Translator("pl")("project.application_sub").lower());self.assertIn("project",Translator("en")("project.application_sub").lower())
    def test_config_persists_language_but_never_passwords(self):
        with tempfile.TemporaryDirectory() as td:
            store=ConfigStore(Path(td)/"config.json");store.save({"language":"pl","store_password":"nope"});data=store.load();self.assertEqual(data.get("language"),"pl");self.assertNotIn("store_password",data)
    def test_translation_catalogs_have_identical_keys(self):self.assertEqual(set(STRINGS["pl"]),set(STRINGS["en"]));[self.assertTrue(STRINGS["pl"][k]) for k in ("tab.home","welcome.title","home.build_now","engine.prepare")]
    def test_onboarding_flag_is_safe_to_persist(self):
        with tempfile.TemporaryDirectory() as td:
            store=ConfigStore(Path(td)/"config.json");store.save({"onboarding_done":True,"language":"pl","key_password":"never-save"});data=store.load();self.assertTrue(data.get("onboarding_done"));self.assertNotIn("key_password",data)
    def test_invalid_package_is_rejected(self):cfg=ProjectConfig(package_name="com..broken");self.assertTrue(cfg.validate());cfg.package_name="1com.example.app";self.assertTrue(cfg.validate())
    def test_api_34_is_rejected_for_play_profile(self):self.assertTrue(any("API 36" in e for e in ProjectConfig(target_sdk=34).validate()))
    def test_generator_is_deterministic_and_has_no_plaintext_signing_password(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"project";cfg=ProjectConfig(app_name='Ghost & "Safe"',package_name="com.swir.ghostsafe",target_sdk=36,signing_enabled=False,output_dir=td);AndroidProjectGenerator().generate(root,cfg);gradle=(root/"app"/"build.gradle.kts").read_text(encoding="utf-8");manifest=(root/"app"/"src"/"main"/"AndroidManifest.xml").read_text(encoding="utf-8");self.assertIn("compileSdk = 36",gradle);self.assertIn('System.getenv("GHOST_STORE_PASSWORD")',gradle);self.assertNotIn("taskkill",gradle.lower());self.assertIn('usesCleartextTraffic="false"',manifest)
    def test_kotlin_package_is_replaced_not_duplicated(self):out=normalize_kotlin_source("package old.pkg\n\nclass MainActivity {}","com.new.pkg");self.assertTrue(out.startswith("package com.new.pkg"));self.assertNotIn("package old.pkg",out)
    def test_runtime_permissions_and_default_icons_are_generated(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"project";cfg=ProjectConfig(app_name="Ghost Runtime",package_name="com.swir.ghostruntime",permission_camera=True,permission_microphone=True,target_sdk=36,output_dir=td);AndroidProjectGenerator().generate(root,cfg);pkg=root/"app"/"src"/"main"/"java"/"com"/"swir"/"ghostruntime";self.assertIn("GhostPermissions.requestMissing(this)",(pkg/"MainActivity.kt").read_text(encoding="utf-8"));self.assertTrue((root/"app"/"src"/"main"/"res"/"mipmap-xxxhdpi"/"ic_launcher.png").is_file())
    def test_sdk_provisioning_requires_explicit_license_acceptance(self):
        with tempfile.TemporaryDirectory() as td:
            paths=Paths(td);sdk=paths.sdk;manager=sdk/"cmdline-tools"/"latest"/"bin"/"sdkmanager.bat";manager.parent.mkdir(parents=True,exist_ok=True);manager.write_text("echo sdk",encoding="utf-8");toolchain=ToolchainManager(paths)
            with mock.patch.object(toolchain,"java_home",return_value=Path(td)/"jdk"),mock.patch.object(toolchain,"gradle_exe",return_value=Path(td)/"gradle.bat"),mock.patch.object(toolchain,"sdk_root",return_value=sdk),mock.patch.object(toolchain,"bundletool_jar",return_value=Path(td)/"bundletool.jar"):
                with self.assertRaises(PermissionError):toolchain.provision(accept_android_sdk_license=False)
    def test_force_managed_mode_ignores_system_java_home(self):
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td)/"system-jdk";(fake/"bin").mkdir(parents=True)
            for name in ("java.exe","keytool.exe","jarsigner.exe"):(fake/"bin"/name).write_text("x",encoding="utf-8")
            toolchain=ToolchainManager(Paths(Path(td)/"ghost"))
            with mock.patch.dict("os.environ",{"JAVA_HOME":str(fake),"GHOST_FORCE_MANAGED_TOOLCHAIN":"1"},clear=False):self.assertIsNone(toolchain.java_home())
    def test_paths_are_private_to_ghost(self):
        with tempfile.TemporaryDirectory() as td:p=Paths(td);self.assertEqual(p.root,Path(td));self.assertTrue(p.workspace.exists())
    def test_project_profile_roundtrip_includes_source(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"demo.ghostproject";cfg=ProjectConfig(app_name="Profile Demo",package_name="com.swir.profile",custom_source="class MainActivity {}",metadata={"note":"ok"});save_project(path,cfg);loaded=load_project(path);self.assertEqual(loaded.app_name,"Profile Demo");self.assertEqual(loaded.custom_source,"class MainActivity {}");self.assertEqual(loaded.metadata.get("note"),"ok")
    def test_project_profile_never_persists_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"safe.ghostproject";cfg=ProjectConfig(metadata={"store_password":"hidden","nested":{"key_password":"hidden2","safe":"yes"}});save_project(path,cfg);raw=path.read_text(encoding="utf-8");self.assertNotIn("hidden",raw);self.assertNotIn("key_password",raw);self.assertIn("safe",raw)
    def test_recent_projects_deduplicates_and_limits(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);paths=[]
            for i in range(5):
                p=root/f"{i}.ghostproject";save_project(p,ProjectConfig(app_name=f"P{i}"));paths.append(p)
            recent=RecentProjects(root/"recent.json",limit=3)
            for p in paths:recent.add(p)
            recent.add(paths[-1]);items=recent.load();self.assertEqual(len(items),3);self.assertEqual(items[0],str(paths[-1]));self.assertEqual(len(items),len(set(items)))
    def test_play_readiness_blocks_unsigned_debug(self):
        report=check_play_readiness(ProjectConfig(build_mode="Debug",export_format="APK",signing_enabled=False,target_sdk=36));codes={x.code for x in report.errors};self.assertFalse(report.ready);self.assertIn("play_release_required",codes);self.assertIn("play_signing_required",codes)
    def test_play_readiness_accepts_signed_release_aab(self):
        with tempfile.TemporaryDirectory() as td:
            key=Path(td)/"release.jks";key.write_text("placeholder",encoding="utf-8");icon=Path(td)/"icon.png";icon.write_bytes(b"png");cfg=ProjectConfig(build_mode="Release",export_format="AAB",signing_enabled=True,keystore_path=str(key),key_alias="ghost",icon_path=str(icon),target_sdk=36);report=check_play_readiness(cfg);self.assertTrue(report.ready);self.assertEqual(report.errors,())
    def test_build_history_records_artifact_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);artifact=root/"demo.apk";artifact.write_bytes(b"ghost-apk");store=BuildHistoryStore(root/"history.json",limit=5);item=store.record(artifact,ProjectConfig(app_name="Demo",package_name="com.swir.demo",version_name="2.1",version_code=7,export_format="APK",build_mode="Release",signing_enabled=True),12.345);self.assertEqual(item["app_name"],"Demo");self.assertTrue(item["signed"]);self.assertEqual(item["duration_seconds"],12.35);self.assertEqual(len(item["sha256"]),64);self.assertEqual(store.load()[0]["artifact"],str(artifact.resolve()))
    def test_certificate_fingerprint_parser(self):
        text="Certificate fingerprints:\n\t SHA1: AA:BB:CC:DD\n\t SHA256: 11:22:33:44:55\n";found=parse_keytool_fingerprints(text);self.assertEqual(found["SHA1"],"AA:BB:CC:DD");self.assertEqual(found["SHA256"],"11:22:33:44:55")
    def test_keytool_password_is_not_in_process_arguments(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);keytool=root/"keytool.exe";keytool.write_text("x",encoding="utf-8");toolchain=mock.Mock();toolchain.keytool_exe.return_value=keytool;toolchain.env.return_value={};builder=GhostBuilder(toolchain);secret="UltraSecret123";target=root/"release.jks"
            completed=mock.Mock(returncode=0,stdout="",stderr="")
            with mock.patch("ghost_builder.builder.subprocess.run",return_value=completed) as run:builder.generate_keystore(target,secret,"ghost")
            args=run.call_args.args[0];env=run.call_args.kwargs["env"];self.assertNotIn(secret,args);self.assertEqual(env["GHOST_KEYTOOL_STOREPASS"],secret);self.assertEqual(env["GHOST_KEYTOOL_KEYPASS"],secret);self.assertIn("-storepass:env",args);self.assertIn("-keypass:env",args)
if __name__=="__main__":unittest.main()
