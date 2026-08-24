const http = require("node:http");
const { URL } = require("node:url");
const crypto = require("node:crypto");
const records = new Map([["1", { task: { id: "1", title: "calibrate", done: false }, version: 1 }]]);
let nextId = 2;
const sabotage = process.env.LAB_SABOTAGE || "";
const tag = r => sabotage === "off-by-one" ? `"v${r.version}"` : `"${crypto.createHash("sha256").update(JSON.stringify(r.task) + ":" + r.version).digest("hex").slice(0, 16)}"`;
function send(res, status, body, etag) { const data = body === undefined ? "" : JSON.stringify(body); const h = { "content-type": "application/json", "content-length": Buffer.byteLength(data) }; if (etag) h.etag = etag; res.writeHead(status, h); res.end(data); }
function read(req) { return new Promise((resolve, reject) => { let d=""; req.on("data",c=>d+=c); req.on("end",()=>{try{resolve(d?JSON.parse(d):{})}catch(e){reject(e)}}); }); }
function precondition(req, rec) { if (!req.headers["if-match"]) return 428; if (req.headers["if-match"] !== tag(rec)) return sabotage === "missing-error-branch" ? 0 : 412; return 0; }
const server = http.createServer(async (req,res) => {
  const url = new URL(req.url,"http://localhost"), m=url.pathname.match(/^\/tasks(?:\/([^/]+))?$/); if(!m)return send(res,404,{error:"not found"}); const id=m[1];
  try {
    if(req.method==="GET"&&!id)return send(res,200,[...records.values()].map(x=>x.task));
    if(req.method==="POST"&&!id){const b=await read(req), t={id:String(nextId++),title:b.title,done:!!b.done},r={task:t,version:1};records.set(t.id,r);return send(res,201,t,tag(r));}
    const rec=id&&records.get(id); if(!rec)return send(res,404,{error:"not found"});
    if(req.method==="GET")return send(res,200,rec.task,tag(rec));
    if(["PUT","PATCH","DELETE"].includes(req.method)){const p=precondition(req,rec);if(p)return send(res,p==412&&sabotage==="wrong-status-code"?409:p,{error:"precondition"});}
    if(req.method==="DELETE"){records.delete(id);return send(res,204);}
    if(req.method==="PUT"||req.method==="PATCH"){
      const before=tag(rec), b=await read(req); if(sabotage==="unhandled-concurrent-update") await new Promise(r=>setTimeout(r,80));
      const current=records.get(id); if(sabotage!=="unhandled-concurrent-update" && sabotage!=="missing-error-branch" && (!current || tag(current)!==before))return send(res,sabotage==="wrong-status-code"?409:412,{error:"precondition"});
      rec.task=req.method==="PUT"?{id,title:b.title,done:!!b.done}:{...rec.task,...b,id}; if(sabotage!=="off-by-one")rec.version++; records.set(id,rec); return send(res,200,rec.task,tag(rec));
    }
    return send(res,405,{error:"method not allowed"});
  } catch { return send(res,400,{error:"invalid json"}); }
});
server.listen(Number(process.env.PORT||8080),"0.0.0.0",()=>console.log("ready"));
