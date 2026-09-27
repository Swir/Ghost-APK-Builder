#!/usr/bin/env python3
"""Read a hash-pinned PC snapshot and adapt a copy in this Android-only tree."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
PIN='31298cc732c97ff90230c3743cd1c3be17f40b6c'
LIB='4ca2500e72c2696a0843c5a132740942851e17f1'
CARGO='8c8a490d12a89f7784cad76425bbb22705d32830'
URL='https://github.com/Swir/Konofix.git'
def git(args,cwd):
    return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True,text=True,timeout=180).stdout.strip()
def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def fn_replace(source,name,new):
    pattern=rf'(?ms)^(?:#\[tauri::command\]\n)?(?:pub )?(?:async )?fn {re.escape(name)}\([^\n]*(?:\n.*?)?^\}}'
    source,n=re.subn(pattern,lambda _:new,source)
    if n!=1: raise RuntimeError(f'Expected one function {name}, found {n}')
    return source
if ROOT.name.casefold()=='konofix' or (ROOT/'.konofix-android').read_text().strip()!='konofix-android-isolated-v1':
    raise RuntimeError('Android isolation marker missing or PC directory selected')
probe=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,capture_output=True,text=True)
if probe.returncode==0:
    if Path(probe.stdout.strip()).resolve()!=ROOT: raise RuntimeError('Nested git workspace refused')
    remotes=git(['remote','-v'],ROOT).lower()
    if re.search(r'github\.com[/:]swir/konofix(?:\.git)?(?:\s|$)',remotes): raise RuntimeError('PC remote refused')
for relative in ['src-tauri','src-tauri/generated']:
    target=ROOT/relative
    if target.is_symlink() or not target.resolve().is_relative_to(ROOT): raise RuntimeError('Unsafe output path')
dest=ROOT/'src-tauri/generated'
if dest.exists(): raise RuntimeError('Generated output already exists; refusing overwrite')
with tempfile.TemporaryDirectory(prefix='konofix-readonly-') as t:
    checkout=Path(t)/'pc';checkout.mkdir()
    git(['init','-q'],checkout)
    git(['config','core.autocrlf','false'],checkout)
    git(['fetch','--depth=1','--no-tags',URL,PIN],checkout)
    if git(['rev-parse','FETCH_HEAD'],checkout)!=PIN: raise RuntimeError('Commit mismatch')
    git(['checkout','--detach','--quiet',PIN],checkout)
    lib=(checkout/'src-tauri/src/lib.rs').read_bytes()
    cargo=(checkout/'src-tauri/Cargo.toml').read_bytes()
    if blob(lib)!=LIB or blob(cargo)!=CARGO: raise RuntimeError('Upstream blob mismatch')
    source=lib.decode()
    for text in ['const WORLD_TOPIC: &str = "konofix/world/v3";','const KAD_PROTOCOL: &str = "/konofix/kad/1.0.0";','const FILE_PROTOCOL: &str = "/konofix/file/1.0.0";','/konofix/4.0']:
        if text not in source: raise RuntimeError('Protocol mismatch: '+text)
    for name in ['offer_file','publish_public_file']:
        source=fn_replace(source,name,'// Desktop picker excluded from Android text interoperability candidate.')
    if 'rfd::' in source: raise RuntimeError('Unreviewed desktop picker remains')
    source=fn_replace(source,'download_directory','fn download_directory() -> Result<PathBuf, String> {\n    mobile_storage("downloads")\n}')
    source=fn_replace(source,'preview_directory','fn preview_directory() -> Result<PathBuf, String> {\n    mobile_storage("previews")\n}')
    source=source.replace('#[cfg_attr(mobile, tauri::mobile_entry_point)]\n','')
    source=fn_replace(source,'run','''static MOBILE_DATA_ROOT: std::sync::OnceLock<PathBuf> = std::sync::OnceLock::new();
fn mobile_storage(child: &str) -> Result<PathBuf, String> {
    MOBILE_DATA_ROOT.get().map(|root| root.join(child))
        .ok_or_else(|| "Android storage not initialized".to_string())
}
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let root = app.path().app_data_dir()?;
            std::fs::create_dir_all(&root)?;
            MOBILE_DATA_ROOT.set(root).map_err(|_| std::io::Error::other("Storage initialized twice"))?;
            Ok(())
        })
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![start_network, send_message, add_bootstrap, refresh_discovery, set_private_messages_enabled, reject_file, disconnect_network])
        .run(tauri::generate_context!())
        .expect("Konofix Android startup failed");
}''')
    anchor='let mut private_messages_enabled = true;'
    if source.count(anchor)!=1: raise RuntimeError('Unexpected private-message policy')
    source=source.replace(anchor,'let mut private_messages_enabled = false;',1)
    (dest/'src').mkdir(parents=True)
    imported={}
    for p in sorted((checkout/'src-tauri/src').glob('*.rs')):
        if p.is_symlink(): raise RuntimeError('Source symlink refused')
        imported[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
        if p.name not in ['main.rs','lib.rs']: shutil.copyfile(p,dest/'src'/p.name)
    (dest/'src/lib.rs').write_text(source)
    shutil.copyfile(checkout/'src-tauri/bootstrap-pool.json',dest/'bootstrap-pool.json')
    lock=checkout/'src-tauri/Cargo.lock'
    if lock.exists(): shutil.copyfile(lock,ROOT/'src-tauri/Cargo.lock')
    for p in checkout.glob('LICENSE*'):
        if p.is_file() and not p.is_symlink(): shutil.copyfile(p,dest/p.name)
    report={'upstreamCommit':PIN,'upstreamVersion':'0.5.1','originalUnmodified':True,'compiled':False,'deviceInteropVerified':False,'importedFilesSha256':imported,'generatedLibSha256':hashlib.sha256(source.encode()).hexdigest()}
    (dest/'import-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
