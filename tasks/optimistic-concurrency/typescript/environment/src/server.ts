import http, {IncomingMessage, ServerResponse} from "node:http";
import {URL} from "node:url";
type Task={id:string,title:string,done:boolean};
const tasks=new Map<string,Task>([["1",{id:"1",title:"calibrate",done:false}]]);let nextId=2;
function send(res:ServerResponse,status:number,body?:unknown){const data=body===undefined?"":JSON.stringify(body);res.writeHead(status,{"content-type":"application/json","content-length":Buffer.byteLength(data)});res.end(data)}
function read(req:IncomingMessage):Promise<Record<string,unknown>>{return new Promise((resolve,reject)=>{let data="";req.on("data",c=>data+=c);req.on("end",()=>{try{resolve(data?JSON.parse(data):{})}catch(e){reject(e)}})})}
const server=http.createServer(async(req,res)=>{const url=new URL(req.url??"/","http://localhost"),m=url.pathname.match(/^\/tasks(?:\/([^/]+))?$/);if(!m)return send(res,404,{error:"not found"});const id=m[1];try{
 if(req.method==="GET"&&!id)return send(res,200,[...tasks.values()]);if(req.method==="POST"&&!id){const b=await read(req),t:Task={id:String(nextId++),title:String(b.title??""),done:Boolean(b.done)};tasks.set(t.id,t);return send(res,201,t)}
 if(!id||!tasks.has(id))return send(res,404,{error:"not found"});if(req.method==="GET")return send(res,200,tasks.get(id));if(req.method==="PUT"||req.method==="PATCH"){const b=await read(req),old=tasks.get(id)!;const t:Task=req.method==="PUT"?{id,title:String(b.title??""),done:Boolean(b.done)}:{...old,...b,id} as Task;tasks.set(id,t);return send(res,200,t)}if(req.method==="DELETE"){tasks.delete(id);return send(res,204)}return send(res,405,{error:"method not allowed"})
 }catch{return send(res,400,{error:"invalid json"})}});server.listen(Number(process.env.PORT||8080),"0.0.0.0",()=>console.log("ready"));
