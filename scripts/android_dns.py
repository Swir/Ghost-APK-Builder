#!/usr/bin/env python3
"""Android-only DNS setup from the active network, never /etc/resolv.conf.
No public resolver is silently substituted. DNS is captured before native startup;
restart the application after changing network during this first interop test.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / '.konofix-android').read_text().strip() != 'konofix-android-isolated-v1':
    raise SystemExit('Isolated Android workspace required')

if sys.argv[1:] == ['--native']:
    lib = ROOT / 'src-tauri/generated/src/lib.rs'
    report_path = ROOT / 'src-tauri/generated/import-report.json'
    report = json.loads(report_path.read_text())
    source = lib.read_text()
    if hashlib.sha256(source.encode()).hexdigest() != report['generatedLibSha256']:
        raise SystemExit('Unexpected generated core; refusing to patch')
    anchor = '        .with_dns()\n        .map_err(|e| e.to_string())?'
    if source.count(anchor) != 1:
        raise SystemExit('Expected exactly one system DNS construction')
    source = source.replace(anchor, '''        .with_dns_config(mobile_dns_config()?, libp2p::dns::ResolverOpts::default())''', 1)
    source += r'''

// Android has no resolv.conf. Read only the DNS servers captured by MainActivity
// before the native runtime starts. Never choose an unrelated public fallback.
fn mobile_dns_config() -> Result<libp2p::dns::ResolverConfig, String> {
    let raw = std::env::var("KONOFIX_ANDROID_DNS").unwrap_or_default();
    let mut addresses = Vec::<std::net::IpAddr>::new();
    for part in raw.split(',').take(8) {
        if let Ok(ip) = part.trim().parse::<std::net::IpAddr>() {
            if !ip.is_unspecified() && !ip.is_multicast() && !addresses.contains(&ip) {
                addresses.push(ip);
            }
        }
    }
    if addresses.is_empty() {
        return Err("Android DNS is unavailable. Connect to Wi-Fi or mobile data, fully close Konofix Android, and reopen it.".to_string());
    }
    let servers = addresses.into_iter()
        .map(hickory_resolver::config::NameServerConfig::udp_and_tcp)
        .collect();
    Ok(libp2p::dns::ResolverConfig::from_parts(None, Vec::new(), servers))
}
'''
    lib.write_text(source)
    cargo = ROOT / 'src-tauri/Cargo.toml'
    text = cargo.read_text()
    if 'hickory-resolver' in text:
        raise SystemExit('Unexpected direct resolver dependency')
    cargo.write_text(text + '\nhickory-resolver = { version = "0.26", default-features = false }\n')
    report['generatedLibSha256'] = hashlib.sha256(source.encode()).hexdigest()
    report['platformPatches'] = ['Android DNS from active network before native runtime startup; no resolv.conf and no hard-coded public DNS fallback']
    report['networkChangeRequiresAppRestart'] = True
    report_path.write_text(json.dumps(report, indent=2))
    print('Android DNS native patch applied; actual device operation remains unverified')
elif sys.argv[1:] == ['--android']:
    activities = list((ROOT / 'src-tauri/gen/android/app/src/main').rglob('MainActivity.kt'))
    if len(activities) != 1:
        raise SystemExit('Expected one MainActivity')
    activity = activities[0]
    source = activity.read_text()
    anchor = 'class MainActivity : TauriActivity() {'
    if source.count(anchor) != 1:
        raise SystemExit('Unexpected MainActivity structure')
    source = source.replace(anchor, anchor + r'''
    companion object {
        // Set once before super.onCreate starts Rust. Do not mutate the process
        // environment while Rust worker threads might be reading it.
        private var dnsInitialized = false
    }
    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        if (!dnsInitialized) {
            dnsInitialized = true
            try {
                val cm = applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as? android.net.ConnectivityManager
                val network = cm?.activeNetwork
                val properties = if (network != null) cm?.getLinkProperties(network) else null
                val servers = properties?.dnsServers?.mapNotNull { it.hostAddress }
                    ?.filter { !it.contains('%') }?.distinct()?.take(8)?.joinToString(",") ?: ""
                android.system.Os.setenv("KONOFIX_ANDROID_DNS", servers, true)
                Log.i("Konofix", "Active-network DNS configuration captured")
            } catch (e: Exception) {
                Log.w("Konofix", "Could not capture active-network DNS", e)
            }
        }
        super.onCreate(savedInstanceState)
    }
''', 1)
    activity.write_text(source)
    print('Native Android DNS capture inserted before Tauri startup')
else:
    raise SystemExit('Use --native or --android')
