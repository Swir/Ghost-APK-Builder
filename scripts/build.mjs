import {cp,mkdir,rm,readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
if((await readFile(path.join(root,'.konofix-android'),'utf8')).trim()!=='konofix-android-isolated-v1')throw Error('Not the isolated Android workspace');
await rm(path.join(root,'dist'),{recursive:true,force:true});
await mkdir(path.join(root,'dist'),{recursive:true});
await cp(path.join(root,'web'),path.join(root,'dist'),{recursive:true});
console.log('Frontend bundled; this is not APK or interoperability verification.');
