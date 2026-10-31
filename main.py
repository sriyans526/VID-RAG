import os, re, json, logging
from contextlib import asynccontextmanager
from typing import Optional
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Header, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from db.database import init_db, get_db
from service.auth_service import hash_password, verify_password, create_access_token, decode_access_token
from service.ingestion_service import IngestionService
from service.RAG_service import RAGService
from service.document_service import DocumentService
from service.study_service import StudyService
from langchain_core.documents import Document
import hashlib, uuid, datetime

load_dotenv()
logging.basicConfig(level=logging.INFO)
log=logging.getLogger("vidrag")
services={}

# Small local-development rate limiter. For multi-worker/public deployments use Redis-backed limits.
_rate_buckets={}
def rate_limit(request: Request, key: str, limit: int, window: int=60):
    now=__import__('time').time(); bucket=_rate_buckets.setdefault(key, [])
    bucket[:]=[t for t in bucket if now-t<window]
    if len(bucket)>=limit: raise HTTPException(429, "Rate limit exceeded. Wait a minute and retry.")
    bucket.append(now)

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app=FastAPI(title="VidRAG Advanced API",version="2.0.0",
 description="Multilingual YouTube RAG with JWT authentication, chat history, notes, library and feedback.",lifespan=lifespan)
cors_env=os.getenv("CORS_ORIGINS","http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000")
origins=[x.strip() for x in cors_env.split(",") if x.strip()]
if "*" in origins:
    app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_origin_regex=r"chrome-extension://.*",
     allow_credentials=False,allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type"])
else:
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_origin_regex=r"chrome-extension://.*",
     allow_credentials=True,allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type"])

class Register(BaseModel):
    email: EmailStr
    password: str=Field(min_length=8,max_length=128)
    display_name: str=Field(min_length=1,max_length=80)
class Login(BaseModel):
    email: EmailStr
    password: str
class Process(BaseModel):
    video: str=Field(min_length=6,max_length=500)
    languages: list[str]=Field(default_factory=lambda:["en","hi","es","fr","de","pt","ar","zh-Hans","ja","mr"])
    force: bool=False
class Ask(BaseModel):
    video_id: str=Field(min_length=11,max_length=11)
    query: str=Field(min_length=1,max_length=int(os.getenv("MAX_QUESTION_CHARS","2000")))
    answer_language: str="auto"
    history: list[dict]=Field(default_factory=list)
    top_k: int=Field(default=6,ge=1,le=12)
class Preferences(BaseModel):
    preferred_language: str=Field(default="auto",max_length=12)
class Note(BaseModel):
    video_id: str=Field(min_length=11,max_length=11)
    timestamp: str=Field(default="",max_length=12)
    content: str=Field(min_length=1,max_length=5000)
class Feedback(BaseModel):
    video_id: str=Field(min_length=11,max_length=11)
    rating: int=Field(ge=1,le=5)
    comment: str=Field(default="",max_length=2000)
class LibraryItem(BaseModel):
    video_id: str=Field(min_length=11,max_length=11)
    title: str=Field(default="",max_length=300)
    language: str=Field(default="auto",max_length=12)

def auth_user(authorization: Optional[str]=Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401,"Bearer access token required.")
    try:
        payload=decode_access_token(authorization.split(" ",1)[1].strip())
        uid=int(payload["sub"])
    except (jwt.PyJWTError,ValueError,KeyError,RuntimeError):
        raise HTTPException(401,"Invalid token or JWT_SECRET is not configured.")
    with get_db() as db:
        row=db.execute("SELECT id,email,display_name,preferred_language,role FROM users WHERE id=?",(uid,)).fetchone()
    if not row: raise HTTPException(401,"Account not found.")
    return dict(row)

def get_services():
    if "ingest" not in services: services["ingest"]=IngestionService()
    if "rag" not in services: services["rag"]=RAGService()
    return services["ingest"],services["rag"]

@app.get("/api")
def api_info(): return {"name":"VidRAG Advanced","version":"2.0.0","docs":"/docs","health":"/health"}

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/")
def root():
    index_file = os.path.join(os.path.dirname(__file__), "frontend", "dist", "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return {"name":"VidRAG Advanced","version":"2.0.0","docs":"/docs","health":"/health"}

@app.post("/auth/register",status_code=201)
def register(body:Register):
    email=body.email.lower().strip()
    try:
        with get_db() as db:
            cur=db.execute("INSERT INTO users(email,password_hash,display_name) VALUES(?,?,?)",
              (email,hash_password(body.password),body.display_name.strip()))
            uid=cur.lastrowid
    except Exception as exc:
        if "UNIQUE" in str(exc).upper(): raise HTTPException(409,"Email already registered.")
        raise
    return {"access_token":create_access_token(uid,email),"token_type":"bearer",
      "user":{"id":uid,"email":email,"display_name":body.display_name.strip(),"preferred_language":"auto"}}

@app.post("/auth/login")
def login(body:Login):
    with get_db() as db: row=db.execute("SELECT * FROM users WHERE email=?",(body.email.lower().strip(),)).fetchone()
    if not row or not verify_password(body.password,row["password_hash"]): raise HTTPException(401,"Incorrect email or password.")
    return {"access_token":create_access_token(row["id"],row["email"]),"token_type":"bearer",
      "user":{"id":row["id"],"email":row["email"],"display_name":row["display_name"],"preferred_language":row["preferred_language"]}}

@app.get("/auth/me")
def me(user=Depends(auth_user)): return user

@app.put("/auth/preferences")
def preferences(body:Preferences,user=Depends(auth_user)):
    with get_db() as db: db.execute("UPDATE users SET preferred_language=? WHERE id=?",(body.preferred_language,user["id"]))
    return {"preferred_language":body.preferred_language}

@app.post("/videos/process")
def process_video(body:Process,request:Request,user=Depends(auth_user)):
    rate_limit(request, f"process:{user['id']}", 10)
    try:
        ingest,_=get_services(); result=ingest.ingest_video(body.video,body.languages,body.force)
        with get_db() as db:
            db.execute("""INSERT INTO video_library(user_id,video_id,title,language) VALUES(?,?,?,?)
            ON CONFLICT(user_id,video_id) DO UPDATE SET title=excluded.title,language=excluded.language""",
            (user["id"],result["video_id"],"",body.languages[0] if body.languages else "auto"))
        return result
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception as exc:
        log.exception("Video processing failed")
        raise HTTPException(502,"Video processing failed. Check transcript availability, Qdrant and model configuration.")

@app.post("/ask")
def ask(body:Ask,request:Request,user=Depends(auth_user)):
    rate_limit(request, f"ask:{user['id']}", 30)
    with get_db() as db:
        owned=db.execute("SELECT 1 FROM video_library WHERE user_id=? AND video_id=?",(user["id"],body.video_id)).fetchone()
    if not owned:
        raise HTTPException(403,"Process or add this video to your library before asking questions.")
    try:
        _,rag=get_services()
        lang=body.answer_language or user["preferred_language"]
        result=rag.ask(body.query,body.video_id,lang,body.history,body.top_k)
        with get_db() as db:
            db.execute("INSERT INTO chat_messages(user_id,video_id,role,content) VALUES(?,?,?,?)",
              (user["id"],body.video_id,"user",body.query))
            db.execute("INSERT INTO chat_messages(user_id,video_id,role,content,metadata_json) VALUES(?,?,?,?,?)",
              (user["id"],body.video_id,"assistant",result.get("answer",""),json.dumps(result,ensure_ascii=False)))
        return result
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception:
        log.exception("Answer generation failed")
        raise HTTPException(502,"Answer generation failed. Check that the video is processed and the LLM is configured.")

@app.get("/videos/library")
def library(user=Depends(auth_user)):
    with get_db() as db: rows=db.execute("SELECT video_id,title,language,created_at FROM video_library WHERE user_id=? ORDER BY id DESC",(user["id"],)).fetchall()
    return {"videos":[dict(r) for r in rows]}

@app.post("/videos/library")
def add_library_item(body:LibraryItem,user=Depends(auth_user)):
    with get_db() as db:
        db.execute("""INSERT INTO video_library(user_id,video_id,title,language) VALUES(?,?,?,?)
        ON CONFLICT(user_id,video_id) DO UPDATE SET title=excluded.title,language=excluded.language""",
        (user["id"],body.video_id,body.title,body.language))
    return {"status":"saved","video_id":body.video_id}

@app.delete("/videos/{video_id}")
def delete_video(video_id:str,user=Depends(auth_user)):
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id): raise HTTPException(400,"Invalid video ID.")
    with get_db() as db:
        db.execute("DELETE FROM video_library WHERE user_id=? AND video_id=?",(user["id"],video_id))
        db.execute("DELETE FROM chat_messages WHERE user_id=? AND video_id=?",(user["id"],video_id))
        db.execute("DELETE FROM notes WHERE user_id=? AND video_id=?",(user["id"],video_id))
        refs=db.execute("SELECT COUNT(*) n FROM video_library WHERE video_id=?",(video_id,)).fetchone()["n"]
    if refs==0:
        try:
            _,rag=get_services(); rag.vector_service.delete_video(video_id)
        except Exception: log.exception("Vector cleanup failed")
    return {"status":"deleted"}

@app.get("/history/{video_id}")
def history(video_id:str,limit:int=Query(100,ge=1,le=300),user=Depends(auth_user)):
    with get_db() as db: rows=db.execute("SELECT id,role,content,metadata_json,created_at FROM chat_messages WHERE user_id=? AND video_id=? ORDER BY id DESC LIMIT ?",(user["id"],video_id,limit)).fetchall()
    messages=[]
    for row in reversed(rows):
        item=dict(row)
        try: item["metadata"]=json.loads(item.pop("metadata_json"))
        except Exception: item["metadata"]={}
        messages.append(item)
    return {"messages":messages}

@app.delete("/history/{video_id}")
def clear_history(video_id:str,user=Depends(auth_user)):
    with get_db() as db: db.execute("DELETE FROM chat_messages WHERE user_id=? AND video_id=?",(user["id"],video_id))
    return {"status":"cleared"}

@app.post("/notes",status_code=201)
def create_note(body:Note,user=Depends(auth_user)):
    with get_db() as db:
        cur=db.execute("INSERT INTO notes(user_id,video_id,timestamp,content) VALUES(?,?,?,?)",(user["id"],body.video_id,body.timestamp,body.content))
    return {"id":cur.lastrowid,"video_id":body.video_id,"timestamp":body.timestamp,"content":body.content}

@app.get("/notes/{video_id}")
def list_notes(video_id:str,user=Depends(auth_user)):
    with get_db() as db: rows=db.execute("SELECT id,video_id,timestamp,content,created_at FROM notes WHERE user_id=? AND video_id=? ORDER BY id DESC",(user["id"],video_id)).fetchall()
    return {"notes":[dict(r) for r in rows]}

@app.delete("/notes/{note_id}")
def delete_note(note_id:int,user=Depends(auth_user)):
    with get_db() as db: cur=db.execute("DELETE FROM notes WHERE id=? AND user_id=?",(note_id,user["id"]))
    if cur.rowcount==0: raise HTTPException(404,"Note not found.")
    return {"status":"deleted"}

@app.post("/feedback",status_code=201)
def feedback(body:Feedback,user=Depends(auth_user)):
    with get_db() as db: cur=db.execute("INSERT INTO feedback(user_id,video_id,rating,comment) VALUES(?,?,?,?)",(user["id"],body.video_id,body.rating,body.comment))
    return {"id":cur.lastrowid,"status":"received"}

@app.get("/stats")
def stats(user=Depends(auth_user)):
    with get_db() as db:
        videos=db.execute("SELECT COUNT(*) n FROM video_library WHERE user_id=?",(user["id"],)).fetchone()["n"]
        messages=db.execute("SELECT COUNT(*) n FROM chat_messages WHERE user_id=?",(user["id"],)).fetchone()["n"]
        notes=db.execute("SELECT COUNT(*) n FROM notes WHERE user_id=?",(user["id"],)).fetchone()["n"]
    return {"processed_videos":videos,"chat_messages":messages,"notes":notes}

@app.get("/languages")
def languages():
    return {"languages":[{"code":"auto","name":"Auto-detect"},{"code":"en","name":"English"},{"code":"hi","name":"Hindi"},{"code":"mr","name":"Marathi"},{"code":"bn","name":"Bengali"},{"code":"ta","name":"Tamil"},{"code":"te","name":"Telugu"},{"code":"ur","name":"Urdu"},{"code":"es","name":"Spanish"},{"code":"fr","name":"French"},{"code":"de","name":"German"},{"code":"pt","name":"Portuguese"},{"code":"ar","name":"Arabic"},{"code":"zh","name":"Chinese"},{"code":"ja","name":"Japanese"},{"code":"it","name":"Italian"}]}


# -------------------- Advanced learning and ingestion APIs --------------------
class StudyRequest(BaseModel):
    video_id: str = Field(min_length=11, max_length=80)
    kind: str = Field(default="quiz", pattern="^(quiz|flashcards|summary|mindmap|learning_path)$")
    count: int = Field(default=8, ge=1, le=8)
    difficulty: str = Field(default="medium", pattern="^(beginner|easy|medium|hard|advanced)$")
    language: str = "auto"

class CrossSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    video_ids: list[str] = Field(min_length=1, max_length=20)
    answer_language: str = "auto"
    top_k: int = Field(default=8, ge=1, le=20)

class PlaylistRequest(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
    languages: list[str] = Field(default_factory=lambda:["en","hi","mr","es","fr"])
    max_videos: int = Field(default=10, ge=1, le=50)

class VisionQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1500)

@app.post("/study/generate")
def generate_study(body: StudyRequest, user=Depends(auth_user)):
    with get_db() as db:
        owned_video=db.execute("SELECT 1 FROM video_library WHERE user_id=? AND video_id=?",(user["id"],body.video_id)).fetchone()
        owned_doc=db.execute("SELECT 1 FROM documents WHERE user_id=? AND id=?",(user["id"],body.video_id)).fetchone()
    if not owned_video and not owned_doc:
        raise HTTPException(403,"Source not found in your account library.")
    try:
        ingest, rag = get_services()
        docs = rag.vector_service.search("query: main concepts definitions important facts", body.video_id, k=6)
        if not docs: raise HTTPException(404, "Process the video first so there is source material.")
        source = "\n\n".join(d.page_content.removeprefix("passage: ") for d in docs)
        generator = StudyService(rag.llm)
        result = generator.generate(body.kind, source, body.count, body.difficulty, body.language)
        with get_db() as db:
            db.execute("INSERT INTO study_items(user_id,video_id,item_type,payload_json) VALUES(?,?,?,?)",
                       (user["id"],body.video_id,body.kind,json.dumps(result,ensure_ascii=False)))
        return {"kind":body.kind,"video_id":body.video_id,"content":result,"warning":"AI-generated study material; verify answers against the cited source."}
    except HTTPException: raise
    except ValueError as exc: raise HTTPException(422,str(exc))
    except Exception:
        log.exception("Study generation failed")
        raise HTTPException(502,"Study generation failed. Check LLM configuration and source indexing.")

@app.get("/study/library")
def study_library(video_id: Optional[str]=None, user=Depends(auth_user)):
    with get_db() as db:
        if video_id:
            rows=db.execute("SELECT id,video_id,item_type,payload_json,created_at FROM study_items WHERE user_id=? AND video_id=? ORDER BY id DESC",(user["id"],video_id)).fetchall()
        else:
            rows=db.execute("SELECT id,video_id,item_type,payload_json,created_at FROM study_items WHERE user_id=? ORDER BY id DESC LIMIT 100",(user["id"],)).fetchall()
    return {"items":[{"id":r["id"],"video_id":r["video_id"],"kind":r["item_type"],"content":json.loads(r["payload_json"]),"created_at":r["created_at"]} for r in rows]}

@app.delete("/study/{item_id}")
def delete_study_item(item_id:int,user=Depends(auth_user)):
    with get_db() as db: cur=db.execute("DELETE FROM study_items WHERE id=? AND user_id=?",(item_id,user["id"]))
    if not cur.rowcount: raise HTTPException(404,"Study item not found.")
    return {"status":"deleted"}

@app.post("/documents/upload",status_code=201)
async def upload_document(file: UploadFile=File(...), user=Depends(auth_user)):
    raw=await file.read()
    if not raw: raise HTTPException(400,"Empty file.")
    if len(raw)>20*1024*1024: raise HTTPException(413,"File exceeds 20 MB limit.")
    svc=DocumentService(); doc_id=svc.new_id()
    try:
        pages=svc.extract_text(file.filename or "upload.txt",raw)
        chunks=svc.chunk(doc_id,pages)
        if not chunks: raise ValueError("No extractable text found. Scanned PDFs need OCR, which is not enabled in this build.")
        _,rag=get_services(); count=rag.vector_service.add_documents(chunks,replace=True)
        with get_db() as db:
            db.execute("INSERT INTO documents(id,user_id,filename,mime_type,chunks) VALUES(?,?,?,?,?)",
                       (doc_id,user["id"],(file.filename or "document")[:255],file.content_type or "",count))
        return {"document_id":doc_id,"filename":file.filename,"pages":len(pages),"chunks":count,"status":"indexed"}
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception:
        log.exception("Document upload failed")
        raise HTTPException(502,"Document indexing failed. Check Qdrant and embedding model.")

@app.get("/documents")
def list_documents(user=Depends(auth_user)):
    with get_db() as db: rows=db.execute("SELECT id,filename,mime_type,chunks,created_at FROM documents WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
    return {"documents":[dict(r) for r in rows]}

@app.delete("/documents/{document_id}")
def delete_document(document_id:str,user=Depends(auth_user)):
    with get_db() as db:
        row=db.execute("SELECT id FROM documents WHERE id=? AND user_id=?",(document_id,user["id"])).fetchone()
        if not row: raise HTTPException(404,"Document not found.")
        db.execute("DELETE FROM documents WHERE id=? AND user_id=?",(document_id,user["id"]))
    try:
        _,rag=get_services(); rag.vector_service.delete_video(document_id)
    except Exception: log.exception("Document vector cleanup failed")
    return {"status":"deleted","document_id":document_id}

@app.post("/documents/ask")
def ask_documents(body: CrossSearchRequest,user=Depends(auth_user)):
    # Document IDs are accepted only if owned by this user; video IDs only if in the user's library.
    allowed=[]
    with get_db() as db:
        for source_id in body.video_ids:
            doc=db.execute("SELECT id FROM documents WHERE id=? AND user_id=?",(source_id,user["id"])).fetchone()
            video=db.execute("SELECT video_id FROM video_library WHERE video_id=? AND user_id=?",(source_id,user["id"])).fetchone()
            if doc or video: allowed.append(source_id)
    if not allowed: raise HTTPException(403,"No selected source belongs to this account.")
    try:
        _,rag=get_services(); docs=rag.vector_service.search_many("query: "+body.query,allowed,k=body.top_k)
        return rag.answer_from_docs(body.query,docs,body.answer_language,[],body.top_k)
    except Exception:
        log.exception("Cross-source search failed")
        raise HTTPException(502,"Cross-source search failed. Check Qdrant and model configuration.")

@app.post("/playlists/process")
def process_playlist(body:PlaylistRequest,user=Depends(auth_user)):
    try:
        import yt_dlp
        opts={"extract_flat":"in_playlist","quiet":True,"skip_download":True,"playlistend":body.max_videos}
        with yt_dlp.YoutubeDL(opts) as ydl: info=ydl.extract_info(body.url,download=False)
        entries=(info or {}).get("entries") or []
        ids=[]
        for e in entries[:body.max_videos]:
            vid=e.get("id")
            if vid and re.fullmatch(r"[A-Za-z0-9_-]{11}",vid): ids.append((vid,e.get("title", "")))
        if not ids: raise HTTPException(400,"No video entries found. Check playlist URL and public access.")
        ingest,_=get_services(); results=[]
        for vid,title in ids:
            try:
                result=ingest.ingest_video(vid,body.languages,False)
                with get_db() as db:
                    db.execute("INSERT INTO video_library(user_id,video_id,title,language) VALUES(?,?,?,?) ON CONFLICT(user_id,video_id) DO UPDATE SET title=excluded.title,language=excluded.language",
                      (user["id"],vid,title[:300],body.languages[0] if body.languages else "auto"))
                results.append({"video_id":vid,"title":title,"status":result.get("status"),"chunks":result.get("chunks",0)})
            except Exception as exc: results.append({"video_id":vid,"title":title,"status":"failed","error":str(exc)[:180]})
        return {"playlist_title":info.get("title","Playlist"),"processed":sum(x["status"] in ("processed","already_processed") for x in results),"results":results}
    except HTTPException: raise
    except Exception:
        log.exception("Playlist processing failed")
        raise HTTPException(502,"Playlist processing failed. Check URL, yt-dlp and transcript availability.")

@app.post("/vision/analyze-upload")
async def analyze_uploaded_video(file:UploadFile=File(...), user=Depends(auth_user)):
    filename=file.filename or "video.mp4"
    if not filename.lower().endswith((".mp4",".mov",".mkv",".webm",".avi")):
        raise HTTPException(400,"Upload MP4, MOV, MKV, WEBM or AVI video.")
    raw=await file.read()
    if len(raw)>100*1024*1024: raise HTTPException(413,"Video exceeds 100 MB limit.")
    try:
        from service.vision_service import VisionService
        result=VisionService().describe_frames(raw,filename)
        return {**result,"note":"Frame sampling is sparse and may miss content between sampled frames. Use only videos you are allowed to process."}
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception:
        log.exception("Video frame analysis failed")
        raise HTTPException(502,"Vision analysis failed. A vision-capable model and compatible video codecs are required.")

@app.get("/admin/overview")
def admin_overview(user=Depends(auth_user)):
    if user.get("role")!="admin": raise HTTPException(403,"Admin role required.")
    with get_db() as db:
        users=db.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        videos=db.execute("SELECT COUNT(*) n FROM video_library").fetchone()["n"]
        chats=db.execute("SELECT COUNT(*) n FROM chat_messages").fetchone()["n"]
        docs=db.execute("SELECT COUNT(*) n FROM documents").fetchone()["n"]
        events=db.execute("SELECT event,detail,created_at FROM audit_events ORDER BY id DESC LIMIT 50").fetchall()
    return {"users":users,"library_entries":videos,"chat_messages":chats,"documents":docs,"recent_events":[dict(r) for r in events]}

@app.get("/admin/users")
def admin_users(user=Depends(auth_user)):
    if user.get("role")!="admin": raise HTTPException(403,"Admin role required.")
    with get_db() as db: rows=db.execute("SELECT id,email,display_name,role,created_at FROM users ORDER BY id DESC LIMIT 500").fetchall()
    return {"users":[dict(r) for r in rows]}

@app.get("/system/capabilities")
def capabilities():
    return {"features":{"authentication":True,"multilingual_rag":True,"document_ingestion":["pdf","docx","pptx","txt","md"],"playlist_ingestion":True,"cross_source_search":True,"study_generation":["quiz","flashcards","summary","mindmap","learning_path"],"notes":True,"history":True,"feedback":True,"video_frame_analysis":"optional; requires a vision-capable provider and OpenCV","oauth":"not configured; add provider credentials before enabling","ocr":"not enabled for scanned PDFs","voice":"not included in this build"}}

dist_assets = os.path.join(os.path.dirname(__file__), "frontend", "dist", "assets")
if os.path.isdir(dist_assets):
    app.mount("/assets", StaticFiles(directory=dist_assets), name="static_assets")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
