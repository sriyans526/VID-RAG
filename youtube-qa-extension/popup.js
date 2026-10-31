document.addEventListener("DOMContentLoaded",()=>{
 const chat=document.getElementById("chat"),input=document.getElementById("query");
 const askBtn=document.getElementById("askBtn"),processBtn=document.getElementById("processBtn");
 const language=document.getElementById("language"),status=document.getElementById("status");
 const API="http://127.0.0.1:8000";
 function message(text,who="bot",stamp=null){
   const el=document.createElement("div");el.className="msg "+who;
   const p=document.createElement("div");p.textContent=text;el.appendChild(p);
   if(stamp){const j=document.createElement("span");j.className="jump";j.textContent="Jump to "+stamp;
     j.onclick=async()=>{const tabs=await chrome.tabs.query({active:true,currentWindow:true});if(tabs[0]?.url){const u=new URL(tabs[0].url);const a=stamp.split(":").map(Number);u.searchParams.set("t",String(a.length===2?a[0]*60+a[1]:a[0]||0));chrome.tabs.update(tabs[0].id,{url:u.toString()});}};
     el.appendChild(j);}
   chat.appendChild(el);chat.scrollTop=chat.scrollHeight;
 }
 async function videoId(){const t=await chrome.tabs.query({active:true,currentWindow:true});if(!t[0]?.url)return null;try{const u=new URL(t[0].url);if(u.hostname.includes("youtu.be"))return u.pathname.slice(1).split("/")[0];if(u.hostname.includes("youtube.com"))return u.searchParams.get("v")||u.pathname.match(/\/(?:shorts|embed)\/([^/]+)/)?.[1]||null;}catch(e){}return null;}
 async function api(path,opts={}){const saved=await chrome.storage.local.get(["vidragToken"]);if(!saved.vidragToken)throw Error("No vidragToken. Register/login at /docs and save the returned token in extension storage.");const headers={Authorization:"Bearer "+saved.vidragToken,...opts.headers};if(opts.body)headers["Content-Type"]="application/json";const r=await fetch(API+path,{...opts,headers});const d=await r.json().catch(()=>({detail:"Invalid API response"}));if(!r.ok)throw Error(d.detail||"Request failed");return d;}
 processBtn.onclick=async()=>{const id=await videoId();if(!id)return message("Open a YouTube video first.");processBtn.disabled=true;status.textContent="Processing transcript…";try{const d=await api("/videos/process",{method:"POST",body:JSON.stringify({video:id})});status.textContent=d.status;message("Video status: "+d.status+". Chunks added: "+d.chunks+".");}catch(e){status.textContent=e.message;message(e.message);}finally{processBtn.disabled=false;}};
 async function ask(){const q=input.value.trim();if(!q)return;const id=await videoId();if(!id)return message("Open a YouTube video first.");message(q,"user");input.value="";askBtn.disabled=true;status.textContent="Searching transcript…";try{const d=await api("/ask",{method:"POST",body:JSON.stringify({video_id:id,query:q,answer_language:language.value})});message(d.answer||"No answer returned.");(d.segments||[]).forEach(s=>message(s.sentence,"bot",s.timestamp));if(d.key_points?.length)message("Key points:\n• "+d.key_points.join("\n• "));status.textContent="Answer generated. Verify important details against the video.";}catch(e){status.textContent=e.message;message(e.message);}finally{askBtn.disabled=false;}}
 askBtn.onclick=ask;input.addEventListener("keydown",e=>{if(e.key==="Enter")ask();});
 chrome.storage.local.get(["vidragToken"],r=>{status.textContent=r.vidragToken?"Connected to local API.":"Register at /docs and save token as vidragToken; see README.";});
});
