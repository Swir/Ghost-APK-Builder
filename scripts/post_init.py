from pathlib import Path
import re,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]/'src-tauri/gen/android'
a='http://schemas.android.com/apk/res/android';ET.register_namespace('android',a)
p=root/'app/src/main/AndroidManifest.xml';tree=ET.parse(p);manifest=tree.getroot()
for permission in ['INTERNET','ACCESS_NETWORK_STATE','ACCESS_WIFI_STATE','CHANGE_WIFI_MULTICAST_STATE']:
    name='android.permission.'+permission
    if not any(el.get('{'+a+'}name')==name for el in manifest.findall('uses-permission')):
        ET.SubElement(manifest,'uses-permission',{'{'+a+'}name':name})
for activity in manifest.findall('application/activity'):
    activity.set('{'+a+'}windowSoftInputMode','adjustResize')
tree.write(p,encoding='utf-8',xml_declaration=True)
activities=list((root/'app/src/main').rglob('MainActivity.kt'))
if len(activities)!=1: raise RuntimeError('Expected one generated MainActivity')
p=activities[0];source=p.read_text();package=re.search(r'^package\s+([\w.]+)',source,re.M)
if not package: raise RuntimeError('Missing Android package')
p.write_text('package '+package.group(1)+'''\n
import android.content.Context
import android.net.wifi.WifiManager
import android.util.Log

// TauriActivity is generated in this application's package, not app.tauri.
class MainActivity : TauriActivity() {
    private var multicast: WifiManager.MulticastLock? = null
    override fun onResume() {
        super.onResume()
        try {
            val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            multicast = wifi?.createMulticastLock("KonofixAndroidDiscovery")?.apply {
                setReferenceCounted(false)
                acquire()
            }
        } catch (e: Exception) { Log.w("Konofix", "Multicast discovery lock unavailable", e) }
    }
    override fun onPause() {
        try { multicast?.let { if (it.isHeld) it.release() } }
        catch (e: Exception) { Log.w("Konofix", "Multicast lock release failed", e) }
        multicast = null
        super.onPause()
    }
}
''')
print('Android permissions and foreground multicast lifecycle configured')
