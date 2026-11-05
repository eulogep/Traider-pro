import {mkdtempSync,mkdirSync,writeFileSync,existsSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import path from 'node:path';
const root='/private/tmp/codex-counter-v031-d7c34xx6';const tmp=mkdtempSync(path.join(root,'legacy-'));mkdirSync(path.join(tmp,'data'));
const file=path.join(tmp,'data/settings.json');
const port=await new Promise(resolve=>{const s=createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
const child=spawn(process.execPath,[path.join(root,'repo/dist/server/node-build.mjs')],{cwd:tmp,env:{...process.env,PORT:String(port)},stdio:'ignore'});
try {
 const url=`http://127.0.0.1:${port}`;
 for(let i=0;i<100;i++){try{if((await fetch(url+'/api/ping')).ok)break;}catch{}await new Promise(r=>setTimeout(r,50));}
 for(const headers of [{Origin:'https://evil.example','Content-Type':'application/x-www-form-urlencoded'},{Origin:'https://evil.example',Host:'evil.example','Content-Type':'application/x-www-form-urlencoded'}]) {
  writeFileSync(file,'{"audit_marker":true}');
  const r=await fetch(url+'/api/settings/reset',{method:'POST',headers,body:''});
  console.log(JSON.stringify({headers,status:r.status,file_deleted:!existsSync(file)}));
 }
}finally{child.kill();}
