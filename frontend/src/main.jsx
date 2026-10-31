import React,{useEffect,useState} from 'react';import{createRoot}from'react-dom/client';import{BookOpen,Brain,Languages,FileUp,Library,LogOut,PlayCircle,Send,Layers,FileText,RefreshCw,Trash2,Menu,ShieldCheck,Search,GraduationCap,Video}from'lucide-react';import'./styles.css';import'./study.css';
const API = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' && !window.location.origin.includes('localhost') && !window.location.origin.includes('127.0.0.1') ? window.location.origin : 'http://127.0.0.1:8000');
function App(){const[token,setToken]=useState(localStorage.getItem('vidrag_token')||'');const[user,setUser]=useState(null);const[authMode,setAuthMode]=useState('login');const[email,setEmail]=useState('');const[password,setPassword]=useState('');const[name,setName]=useState('');const[video,setVideo]=useState('');const[q,setQ]=useState('');const[lang,setLang]=useState('auto');const[answer,setAnswer]=useState(null);const[busy,setBusy]=useState(false);const[notice,setNotice]=useState('');const[tab,setTab]=useState('ask');const[docs,setDocs]=useState([]);const[library,setLibrary]=useState([]);const[notes,setNotes]=useState([]);const[note,setNote]=useState('');const[study,setStudy]=useState(null);const[file,setFile]=useState(null);const[playlist,setPlaylist]=useState('');
const headers=()=>({'Content-Type':'application/json',Authorization:`Bearer ${token}`});async function api(path,opts={}){const res=await fetch(API+path,{...opts,headers:{...headers(),...(opts.headers||{})}});const data=await res.json().catch(()=>({detail:'Unexpected API response'}));if(!res.ok)throw Error(data.detail||`HTTP ${res.status}`);return data}
useEffect(()=>{if(token)api('/auth/me').then(setUser).catch(()=>{localStorage.removeItem('vidrag_token');setToken('');setUser(null)})},[token]);useEffect(()=>{if(token){refreshLibrary();refreshDocs()}},[token]);async function auth(e){e.preventDefault();setBusy(true);setNotice('');try{const data=await fetch(API+(authMode==='login'?'/auth/login':'/auth/register'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(authMode==='login'?{email,password}:{email,password,display_name:name})}).then(async r=>{const d=await r.json();if(!r.ok)throw Error(d.detail||'Authentication failed');return d});localStorage.setItem('vidrag_token',data.access_token);setToken(data.access_token);setUser(data.user);setNotice('Signed in successfully.')}catch(e){setNotice(e.message)}finally{setBusy(false)}}
async function refreshLibrary(){try{setLibrary((await api('/videos/library')).videos)}catch(e){setNotice(e.message)}}async function refreshDocs(){try{setDocs((await api('/documents')).documents)}catch{}}
async function process(){if(!video.trim())return setNotice('Enter a YouTube URL or video ID first.');setBusy(true);setNotice('Processing transcript and creating vector index…');try{const d=await api('/videos/process',{method:'POST',body:JSON.stringify({video,languages:['en','hi','mr','es','fr','de','pt','ar','zh-Hans','ja'],force:false})});setNotice(`Video ${d.status}; ${d.chunks||0} chunks indexed.`);await refreshLibrary()}catch(e){setNotice(e.message)}finally{setBusy(false)}}
async function ask(e){e?.preventDefault();if(!q.trim()||!video.trim())return setNotice('Enter a YouTube video URL/ID and a question.');setBusy(true);setAnswer(null);setNotice('Searching evidence and generating answer…');try{const id=(video.match(/(?:v=|youtu\.be\/|shorts\/|embed\/)?([A-Za-z0-9_-]{11})/)||[])[1]||video;const d=await api('/ask',{method:'POST',body:JSON.stringify({video_id:id,query:q,answer_language:lang,top_k:6,history:[]})});setAnswer(d);setNotice('Answer ready. Verify important details against the cited source.')}catch(e){setNotice(e.message)}finally{setBusy(false)}}
async function generate(kind){if(!video.trim())return setNotice('Choose and process a YouTube video first.');setBusy(true);setNotice(`Generating ${kind}…`);try{const id=(video.match(/(?:v=|youtu\.be\/|shorts\/|embed\/)?([A-Za-z0-9_-]{11})/)||[])[1]||video;const d=await api('/study/generate',{method:'POST',body:JSON.stringify({video_id:id,kind,count:8,difficulty:'medium',language:lang})});setStudy({kind,content:d.content});setTab('study');setNotice(`${kind} generated and saved.`)}catch(e){setNotice(e.message)}finally{setBusy(false)}}
async function upload(){if(!file)return setNotice('Choose a PDF, DOCX, PPTX, TXT or MD file.');setBusy(true);try{const fd=new FormData();fd.append('file',file);const r=await fetch(API+'/documents/upload',{method:'POST',headers:{Authorization:`Bearer ${token}`},body:fd});const d=await r.json();if(!r.ok)throw Error(d.detail||'Upload failed');setNotice(`Indexed ${d.filename}: ${d.chunks} chunks.`);setFile(null);refreshDocs()}catch(e){setNotice(e.message)}finally{setBusy(false)}}
async function addNote(){if(!note.trim())return;try{const id=(video.match(/(?:v=|youtu\.be\/|shorts\/|embed\/)?([A-Za-z0-9_-]{11})/)||[])[1]||video;await api('/notes',{method:'POST',body:JSON.stringify({video_id:id,timestamp:'',content:note})});setNotes([...notes,note]);setNote('');setNotice('Note saved.')}catch(e){setNotice(e.message)}}
async function crossSearch(e){e.preventDefault();if(!q.trim())return;setBusy(true);try{const ids=library.map(x=>x.video_id);const docids=docs.map(x=>x.id);const d=await api('/documents/ask',{method:'POST',body:JSON.stringify({query:q,video_ids:[...ids,...docids].slice(0,20),answer_language:lang,top_k:8})});setAnswer(d);setNotice('Cross-source answer ready.')}catch(e){setNotice(e.message)}finally{setBusy(false)}}
if(!token||!user)return <div className="auth-wrap"><div className="auth-card"><div className="brand-mark"><PlayCircle size={28}/></div><p className="eyebrow">MULTIMODAL LEARNING INTELLIGENCE</p><h1>VidRAG</h1><p className="muted">Understand videos. Learn in your language.</p><form onSubmit={auth}><label>Email<input type="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/></label>{authMode==='register'&&<label>Display name<input required value={name} onChange={e=>setName(e.target.value)} placeholder="Your name"/></label>}<label>Password<input type="password" minLength="8" required value={password} onChange={e=>setPassword(e.target.value)} placeholder="At least 8 characters"/></label><button className="primary full" disabled={busy}>{busy?'Please wait…':authMode==='login'?'Sign in':'Create account'}</button></form><button className="link-btn" onClick={()=>setAuthMode(authMode==='login'?'register':'login')}>{authMode==='login'?"Don't have an account? Register":"Already have an account? Sign in"}</button>{notice&&<p className="notice">{notice}</p>}<p className="fine">Your data is stored by the API configured for this app. Use only content you are allowed to process.</p></div></div>;
return <div className="app"><aside className="sidebar"><div className="brand"><div className="brand-mark"><PlayCircle/></div><div><b>VidRAG</b><small>AI learning workspace</small></div></div><div className="nav-label">WORKSPACE</div>{[['ask',PlayCircle,'Video Q&A'],['study',GraduationCap,'Study studio'],['documents',FileText,'Documents'],['library',Library,'My library']].map(([id,Icon,label])=><button key={id} className={'nav-item '+(tab===id?'active':'')} onClick={()=>setTab(id)}><Icon size={18}/>{label}</button>)}<div className="sidebar-bottom"><div className="user-card"><div className="avatar">{(user.display_name||'U').slice(0,1).toUpperCase()}</div><div><b>{user.display_name}</b><small>{user.email}</small></div></div><button className="nav-item" onClick={()=>{localStorage.removeItem('vidrag_token');setToken('');setUser(null)}}><LogOut size={17}/>Sign out</button><small className="fine">API: {API}</small></div></aside><main className="main"><header className="topbar"><div><span className="eyebrow">YOUR PERSONAL AI TUTOR</span><h2>{({ask:'Video intelligence',study:'Study studio',documents:'Knowledge sources',library:'Your library'})[tab]}</h2></div><div className="top-actions"><span className="status-pill"><span/> API session</span><select value={lang} onChange={e=>setLang(e.target.value)} aria-label="Answer language"><option value="auto">Auto language</option><option value="en">English</option><option value="hi">Hindi</option><option value="mr">Marathi</option><option value="bn">Bengali</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="es">Spanish</option><option value="fr">French</option><option value="de">German</option><option value="ar">Arabic</option><option value="zh">Chinese</option><option value="ja">Japanese</option></select></div></header>{notice&&<div className="notice-bar">{notice}<button onClick={()=>setNotice('')}>×</button></div>}
{tab==='ask'&&<><section className="hero"><div><span className="pill">MULTILINGUAL RAG</span><h1>Turn any lecture into<br/><em>understanding.</em></h1><p>Ask grounded questions, jump to evidence, and learn at your own pace.</p></div><div className="hero-art"><Brain size={84}/><span className="orbit o1"/><span className="orbit o2"/></div></section><section className="panel source-panel"><div className="section-heading"><div><h3>Choose a YouTube video</h3><p>Public videos with accessible transcripts are supported.</p></div><button className="secondary" onClick={refreshLibrary}><RefreshCw size={15}/> Refresh</button></div><div className="input-row"><input value={video} onChange={e=>setVideo(e.target.value)} placeholder="Paste YouTube URL or 11-character video ID"/><button className="primary" disabled={busy} onClick={process}><PlayCircle size={16}/> Process video</button></div><div className="feature-row"><span><Languages size={15}/> Cross-language questions</span><span><ShieldCheck size={15}/> Source-grounded answers</span><span><Layers size={15}/> Timestamp citations</span></div></section><section className="panel"><div className="section-heading"><div><h3>Ask your video</h3><p>Ask for explanations, definitions, examples or summaries.</p></div></div><form className="ask-row" onSubmit={ask}><textarea value={q} onChange={e=>setQ(e.target.value)} placeholder="What are the three main ideas explained in this video?" rows="2"/><button className="primary send" disabled={busy}><Send size={17}/></button></form>{answer&&<Answer answer={answer}/>}<div className="quick-actions"><button onClick={()=>generate('summary')} disabled={busy}><FileText size={16}/> Summary</button><button onClick={()=>generate('quiz')} disabled={busy}><Brain size={16}/> Generate quiz</button><button onClick={()=>generate('flashcards')} disabled={busy}><Layers size={16}/> Flashcards</button><button onClick={()=>generate('mindmap')} disabled={busy}><BookOpen size={16}/> Mind map</button></div></section></>}
{tab==='study'&&<section className="panel"><div className="section-heading"><div><h3>AI study studio</h3><p>Generate learning assets grounded in the current video transcript.</p></div></div><div className="study-grid">{[['summary','Structured summary','Study notes and key terms',FileText],['quiz','Practice quiz','MCQs with explanations',Brain],['flashcards','Flashcards','Recall key concepts',Layers],['mindmap','Mind map','Organize related ideas',BookOpen],['learning_path','Learning path','Build a topic-by-topic plan',GraduationCap]].map(([kind,title,desc,Icon])=><button className="study-card" key={kind} onClick={()=>generate(kind)} disabled={busy}><Icon size={24}/><b>{title}</b><span>{desc}</span></button>)}</div>{study&&<div className="study-result"><div className="section-heading"><h3>{study.kind.replace('_',' ')}</h3><button className="secondary" onClick={()=>navigator.clipboard.writeText(JSON.stringify(study.content,null,2)).then(()=>setNotice('Study content copied.')).catch(()=>setNotice('Copy failed; use a secure browser context.'))}>Copy JSON</button></div><StudyContent kind={study.kind} content={study.content}/></div>}</section>}
{tab==='documents'&&<><section className="panel"><div className="section-heading"><div><h3>Add knowledge documents</h3><p>Upload text-based PDF, Word, PowerPoint, TXT or Markdown files (20 MB max).</p></div><FileUp/></div><div className="upload-box"><input type="file" accept=".pdf,.docx,.pptx,.txt,.md" onChange={e=>setFile(e.target.files?.[0]||null)}/><button className="primary" disabled={busy||!file} onClick={upload}>Upload and index</button></div><p className="fine">Scanned PDFs need OCR; OCR is not enabled in this build. Document content is indexed in the shared vector collection with access controlled by the API.</p></section><section className="panel"><div className="section-heading"><div><h3>Ask across videos and documents</h3><p>Search your saved sources in one question.</p></div></div><form onSubmit={crossSearch} className="input-row"><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Compare the definitions across my sources…"/><button className="primary" disabled={busy}><Search size={16}/> Search sources</button></form>{answer&&<Answer answer={answer}/>}<div className="source-list">{docs.map(d=><div className="source-item" key={d.id}><FileText/><div><b>{d.filename}</b><small>{d.chunks} chunks · {d.created_at}</small></div><button className="icon-btn" onClick={async()=>{try{await api('/documents/'+d.id,{method:'DELETE'});refreshDocs();setNotice('Document deleted.')}catch(e){setNotice(e.message)}}}><Trash2 size={16}/></button></div>)}</div></section></>}
{tab==='library'&&<><section className="panel"><div className="section-heading"><div><h3>Saved videos</h3><p>Videos indexed in your personal library.</p></div><button className="secondary" onClick={refreshLibrary}><RefreshCw size={15}/> Refresh</button></div>{library.length===0?<div className="empty"><Library size={30}/><b>No videos yet</b><span>Process a YouTube video in Video intelligence.</span></div>:library.map(v=><div className="source-item" key={v.video_id}><PlayCircle/><div><b>{v.title||v.video_id}</b><small>{v.video_id} · {v.language} · {v.created_at}</small></div><button className="secondary" onClick={()=>{setVideo('https://www.youtube.com/watch?v='+v.video_id);setTab('ask')}}>Open</button><button className="icon-btn" onClick={async()=>{try{await api('/videos/'+v.video_id,{method:'DELETE'});refreshLibrary();setNotice('Video removed from library.')}catch(e){setNotice(e.message)}}}><Trash2 size={16}/></button></div>)}</section><section className="panel"><div className="section-heading"><div><h3>Playlist ingestion</h3><p>Index up to 10 videos from a public YouTube playlist per request.</p></div></div><div className="input-row"><input value={playlist} onChange={e=>setPlaylist(e.target.value)} placeholder="Paste public YouTube playlist URL"/><button className="primary" disabled={busy} onClick={async()=>{setBusy(true);try{const d=await api('/playlists/process',{method:'POST',body:JSON.stringify({url:playlist,max_videos:10,languages:['en','hi','mr']})});setNotice(`Playlist: ${d.processed} videos processed.`);refreshLibrary()}catch(e){setNotice(e.message)}finally{setBusy(false)}}}><Video size={16}/> Process playlist</button></div></section></>}
<footer>VidRAG Advanced · AI-generated outputs can be wrong. Check original source evidence.</footer></main></div>}
function Answer({answer}){return <div className="answer"><div className="answer-title"><Brain size={18}/><b>VidRAG answer</b><span className="confidence">retrieval indicator {Math.round((answer.confidence||0)*100)}%</span></div><p className="answer-text">{answer.answer}</p>{answer.key_points?.length>0&&<><h4>Key points</h4><ul>{answer.key_points.map((x,i)=><li key={i}>{x}</li>)}</ul></>}{answer.sources?.length>0&&<><h4>Evidence sources</h4>{answer.sources.map((s,i)=><div className="evidence" key={i}><div><b>{s.source_id}</b><span>{s.timestamp||`Page ${s.page||1}`}</span></div><p>{s.text}</p></div>)}</>}{answer.follow_up_questions?.length>0&&<><h4>Explore further</h4><ul>{answer.follow_up_questions.map((x,i)=><li key={i}>{x}</li>)}</ul></>}</div>}

createRoot(document.getElementById('root')).render(<App/>);


// Study presentation components. The API still returns the original JSON;
// these components render it as usable study material instead of a raw dump.
function StudyContent({kind,content}) {
  if (kind === 'flashcards') return <Flashcards cards={content}/>;
  if (kind === 'quiz') return <Quiz questions={content}/>;
  if (kind === 'summary') return <SummaryNotes data={content}/>;
  if (kind === 'mindmap') return <MindMap data={content}/>;
  if (kind === 'learning_path') return <LearningPath data={content}/>;
  return <JsonFallback data={content}/>;
}

function JsonFallback({data}) {
  return <div className="study-fallback"><p>This result has an unexpected format. You can still copy the original JSON.</p><pre>{JSON.stringify(data,null,2)}</pre></div>;
}

function Evidence({quote}) {
  return quote ? <details className="study-evidence"><summary>Show source evidence</summary><blockquote>{quote}</blockquote></details> : null;
}

function Flashcards({cards}) {
  const [order,setOrder] = useState(()=>Array.isArray(cards)?cards.map((_,index)=>index):[]);
  const [index,setIndex] = useState(0);
  const [revealed,setRevealed] = useState(false);
  const [ratings,setRatings] = useState({});
  useEffect(()=>{setOrder(Array.isArray(cards)?cards.map((_,index)=>index):[]);setIndex(0);setRevealed(false);setRatings({})},[cards]);
  useEffect(()=>{
    function onKeyDown(event) {
      if (event.target instanceof HTMLElement&&['INPUT','TEXTAREA','SELECT','BUTTON'].includes(event.target.tagName)) return;
      if (event.code==='Space') {event.preventDefault();setRevealed(value=>!value)}
      if (event.key==='ArrowRight') {setIndex(value=>Math.min(value+1,(cards?.length||1)-1));setRevealed(false)}
      if (event.key==='ArrowLeft') {setIndex(value=>Math.max(0,value-1));setRevealed(false)}
    }
    window.addEventListener('keydown',onKeyDown);
    return ()=>window.removeEventListener('keydown',onKeyDown);
  },[cards]);
  if (!Array.isArray(cards) || !cards.length) return <JsonFallback data={cards}/>;
  const sourceIndex=order[index]??index;
  const card=cards[sourceIndex]||{};
  const learned=Object.values(ratings).filter(rating=>rating==='got-it').length;
  function move(next) {setIndex(next);setRevealed(false)}
  function shuffle() {
    const shuffled=order.slice();
    for(let i=shuffled.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[shuffled[i],shuffled[j]]=[shuffled[j],shuffled[i]]}
    setOrder(shuffled);move(0);
  }
  function rate(rating) {
    setRatings(current=>({...current,[sourceIndex]:rating}));
    if(index<cards.length-1)move(index+1);
  }
  return <div className="study-flashcards">
    <div className="study-tool-row">
      <span>{learned} of {cards.length} mastered</span>
      <button type="button" className="study-text-button" onClick={shuffle}>Shuffle cards</button>
    </div>
    <div className="study-progress-track" role="progressbar" aria-valuenow={index+1} aria-valuemin={0} aria-valuemax={cards.length}>
      <span style={{width:`${((index+1)/cards.length)*100}%`}}/>
    </div>
    <button type="button" className={'study-flip-card'+(revealed?' is-flipped':'')} onClick={()=>setRevealed(value=>!value)} aria-label={revealed?'Show question':'Reveal answer'} aria-pressed={revealed}>
      <span className="study-card-topline"><span>{revealed?'ANSWER':'QUESTION'}</span><span>{index+1} / {cards.length}</span></span>
      <span className="study-card-main">{revealed?(card.back||'No answer was provided for this card.'):card.front||'No question was provided for this card.'}</span>
      <span className="study-card-hint">{revealed?'Think it through, then rate your recall.':'Take a moment to answer before revealing · Space to flip'}</span>
    </button>
    {revealed&&<div className="study-recall-actions" aria-label="Rate your recall">
      <button type="button" className="study-rate-again" onClick={()=>rate('review')}>↻ Need practice</button>
      <button type="button" className="study-rate-known" onClick={()=>rate('got-it')}>✓ Got it</button>
    </div>}
    {revealed&&<Evidence quote={card.evidence_quote}/>}
    <div className="study-controls">
      <button type="button" className="secondary" disabled={index===0} onClick={()=>move(index-1)}>← Previous</button>
      <span className="study-key-hint">Use ← → to navigate · Space to flip</span>
      <button type="button" className="secondary" disabled={index===cards.length-1} onClick={()=>move(index+1)}>Next →</button>
    </div>
    {index===cards.length-1&&ratings[sourceIndex]&&<p className="study-complete-note">You reached the last card. Shuffle to review the full deck again.</p>}
  </div>;
}

function Quiz({questions}) {
  const [answers,setAnswers]=useState({});
  const [checkedQuestions,setCheckedQuestions]=useState({});
  const [index,setIndex]=useState(0);
  useEffect(()=>{setAnswers({});setCheckedQuestions({});setIndex(0)},[questions]);
  if (!Array.isArray(questions)||!questions.length) return <JsonFallback data={questions}/>;
  const item=questions[index]||{};
  const checked=Boolean(checkedQuestions[index]);
  const score=questions.reduce((count,question,i)=>count+(checkedQuestions[i]&&Number(answers[i])===Number(question.answer_index)?1:0),0);
  const answered=Object.keys(checkedQuestions).length;
  const complete=answered===questions.length;
  return <div className="study-quiz">
    <div className="study-tool-row"><span>{complete?`Quiz complete · ${score} / ${questions.length} correct`:`Question ${index+1} of ${questions.length}`}</span><span>{answered} checked</span></div>
    <div className="study-progress-track" role="progressbar" aria-valuenow={answered} aria-valuemin={0} aria-valuemax={questions.length}>
      <span style={{width:`${(answered/questions.length)*100}%`}}/>
    </div>
    {complete&&<div className="study-score-card"><span className="study-score-value">{Math.round((score/questions.length)*100)}%</span><div><b>{score===questions.length?'Perfect score!':score>=questions.length/2?'Nice work!':'Good practice round!'}</b><p>You got {score} of {questions.length} correct. Review any question below or try again.</p></div></div>}
    <nav className="study-question-nav" aria-label="Quiz questions">{questions.map((_,questionIndex)=><button type="button" key={questionIndex} className={(questionIndex===index?'current ':'')+(checkedQuestions[questionIndex]?(Number(answers[questionIndex])===Number(questions[questionIndex].answer_index)?'is-correct':'is-wrong'):'')} onClick={()=>setIndex(questionIndex)} aria-label={`Question ${questionIndex+1}${checkedQuestions[questionIndex]?(Number(answers[questionIndex])===Number(questions[questionIndex].answer_index)?', correct':', incorrect'):''}`}>{questionIndex+1}</button>)}</nav>
    <section className="study-question" key={index}>
      <span className="study-question-kicker">QUESTION {index+1}</span>
      <h4>{item.question}</h4>
      <div className="study-options">{(Array.isArray(item.options)?item.options:[]).map((option,optionIndex)=>{
        const correct=checked&&optionIndex===Number(item.answer_index);
        const wrong=checked&&Number(answers[index])===optionIndex&&!correct;
        return <button type="button" key={optionIndex} className={'study-option'+(Number(answers[index])===optionIndex?' selected':'')+(correct?' correct':'')+(wrong?' wrong':'')} disabled={checked} onClick={()=>setAnswers(old=>({...old,[index]:optionIndex}))}>
          <span className="study-option-letter">{String.fromCharCode(65+optionIndex)}</span><span>{option}</span>{correct&&<strong>✓</strong>}{wrong&&<strong>✕</strong>}
        </button>;
      })}</div>
      {checked&&<div className={'study-explanation '+(Number(answers[index])===Number(item.answer_index)?'is-correct':'is-wrong')}>
        <strong>{Number(answers[index])===Number(item.answer_index)?'That’s right!':'Not quite—here’s why'}</strong>
        <p>{item.explanation||'Review the correct option above and revisit the source evidence.'}</p><Evidence quote={item.evidence_quote}/>
      </div>}
    </section>
    <div className="study-controls">
      <button type="button" className="secondary" disabled={index===0} onClick={()=>setIndex(value=>value-1)}>← Previous</button>
      {!checked?<button type="button" className="primary" disabled={answers[index]===undefined} onClick={()=>setCheckedQuestions(old=>({...old,[index]:true}))}>Check answer</button>:index<questions.length-1?<button type="button" className="primary" onClick={()=>setIndex(value=>value+1)}>Next question →</button>:<button type="button" className="primary" onClick={()=>{setAnswers({});setCheckedQuestions({});setIndex(0)}}>↻ Try again</button>}
      <button type="button" className="study-text-button" onClick={()=>{setAnswers({});setCheckedQuestions({});setIndex(0)}}>Restart quiz</button>
    </div>
  </div>;
}

function SummaryNotes({data}) {
  const [reviewed,setReviewed]=useState({});
  const [openTerms,setOpenTerms]=useState({});
  const [knownQuestions,setKnownQuestions]=useState({});
  useEffect(()=>{setReviewed({});setOpenTerms({});setKnownQuestions({})},[data]);
  if (!data||typeof data!=='object'||Array.isArray(data)) return <JsonFallback data={data}/>;
  const points=Array.isArray(data.key_points)?data.key_points:[];
  const terms=Array.isArray(data.definitions)?data.definitions:[];
  const questions=Array.isArray(data.revision_questions)?data.revision_questions:[];
  const total=points.length+questions.length;
  const progress=Object.values(reviewed).filter(Boolean).length+Object.values(knownQuestions).filter(Boolean).length;
  return <article className="study-notes">
    {data.title&&<h4>{data.title}</h4>}
    {data.summary&&<p>{data.summary}</p>}
    {total>0&&<div className="study-tool-row"><span>Review progress</span><strong>{progress} / {total} checked</strong></div>}
    {total>0&&<div className="study-progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={total}><span style={{width:`${(progress/total)*100}%`}}/></div>}
    {points.length>0&&<section className="study-notes-section">
      <h5>Key points <span>Mark each as you review</span></h5>
      <div className="study-note-list">{points.map((point,index)=><button type="button" key={index} className={'study-note-item'+(reviewed[index]?' is-reviewed':'')} onClick={()=>setReviewed(old=>({...old,[index]:!old[index]}))}>
        <span className="study-check">{reviewed[index]?'✓':index+1}</span><span>{point}</span>
      </button>)}</div>
    </section>}
    {terms.length>0&&<section className="study-notes-section">
      <h5>Key terms <span>Tap a term to reveal its definition</span></h5>
      <div className="study-term-grid">{terms.map((item,index)=><button type="button" key={index} className={'study-term-card'+(openTerms[index]?' is-open':'')} onClick={()=>setOpenTerms(old=>({...old,[index]:!old[index]}))}>
        <span className="study-card-topline">{openTerms[index]?'DEFINITION':'KEY TERM'}</span><strong>{openTerms[index]?(item.definition||'No definition provided.'):item.term||'Term'}</strong>
        <span className="study-card-hint">{openTerms[index]?'Tap to hide definition':'Tap to reveal'}</span>
      </button>)}</div>
    </section>}
    {questions.length>0&&<section className="study-notes-section">
      <h5>Active recall <span>Answer aloud before checking it off</span></h5>
      <div className="study-recall-list">{questions.map((question,index)=><label key={index} className={'study-recall-prompt'+(knownQuestions[index]?' is-reviewed':'')}>
        <input type="checkbox" checked={Boolean(knownQuestions[index])} onChange={()=>setKnownQuestions(old=>({...old,[index]:!old[index]}))}/>
        <span>{question}</span><small>{knownQuestions[index]?'Got it':'Mark as answered'}</small>
      </label>)}</div>
    </section>}
  </article>;
}

function MindMap({data}) {
  const [expanded,setExpanded]=useState({});
  const [explored,setExplored]=useState({});
  useEffect(()=>{setExpanded({});setExplored({})},[data]);
  if (!data||typeof data!=='object'||Array.isArray(data)) return <JsonFallback data={data}/>;
  if (!Array.isArray(data.branches)) return <JsonFallback data={data}/>;
  const branches=data.branches;
  const exploredCount=Object.values(explored).filter(Boolean).length;
  const allExpanded=branches.length>0&&branches.every((_,index)=>expanded[index]);
  return <section className="study-mindmap">
    <div className="study-map-center"><span>YOUR CONCEPT MAP</span><h4>{data.central_topic||'Mind map'}</h4><small>{exploredCount} of {branches.length} branches explored</small></div>
    <div className="study-tool-row"><span>Open a branch to explore its connections</span><button type="button" className="study-text-button" onClick={()=>setExpanded(allExpanded?{}:Object.fromEntries(branches.map((_,index)=>[index,true])))}>{allExpanded?'Collapse all':'Expand all'}</button></div>
    <div className="study-map-branches">{branches.map((branch,index)=>{
      const children=Array.isArray(branch.children)?branch.children:[];
      return <article className={'study-map-branch'+(explored[index]?' is-explored':'')} key={index}>
        <div className="study-map-branch-heading">
          <button type="button" className="study-map-toggle" aria-expanded={Boolean(expanded[index])} onClick={()=>setExpanded(old=>({...old,[index]:!old[index]}))}>
            <span className="study-map-index">{String(index+1).padStart(2,'0')}</span><span className="study-map-topic">{branch.topic||'Topic'}</span><span className="study-map-count">{children.length} connections</span><span>{expanded[index]?'−':'+'}</span>
          </button>
          <button type="button" className="study-map-done" onClick={()=>setExplored(old=>({...old,[index]:!old[index]}))}>{explored[index]?'✓ Explored':'Mark explored'}</button>
        </div>
        {expanded[index]&&<div className="study-map-children">{children.length?children.map((child,childIndex)=><div className="study-map-child" key={childIndex}><span>↳</span>{child}</div>):<p>No related concepts were provided for this branch.</p>}</div>}
      </article>;
    })}</div>
  </section>;
}

function LearningPath({data}) {
  const [completed,setCompleted]=useState({});
  const [expanded,setExpanded]=useState({});
  useEffect(()=>{setCompleted({});setExpanded({})},[data]);
  if (!data||typeof data!=='object'||Array.isArray(data)) return <JsonFallback data={data}/>;
  if (!Array.isArray(data.steps)) return <JsonFallback data={data}/>;
  const steps=data.steps;
  const completeCount=Object.values(completed).filter(Boolean).length;
  return <section className="study-path">
    <div className="study-path-header"><div><span>YOUR LEARNING JOURNEY</span>{data.goal&&<h4>{data.goal}</h4>}</div><strong>{completeCount} / {steps.length} complete</strong></div>
    <div className="study-progress-track" role="progressbar" aria-valuenow={completeCount} aria-valuemin={0} aria-valuemax={steps.length}><span style={{width:`${steps.length?(completeCount/steps.length)*100:0}%`}}/></div>
    <ol className="study-path-steps">{steps.map((step,index)=><li className={'study-path-step'+(completed[index]?' is-complete':'')} key={index}>
      <span className="study-path-marker">{completed[index]?'✓':index+1}</span>
      <div className="study-path-step-content">
        <button type="button" className="study-path-step-toggle" aria-expanded={Boolean(expanded[index])} onClick={()=>setExpanded(old=>({...old,[index]:!old[index]}))}>
          <span><small>STEP {String(index+1).padStart(2,'0')}</small><strong>{step.title||`Step ${index+1}`}</strong></span><span>{expanded[index]?'−':'+'}</span>
        </button>
        {expanded[index]&&<div className="study-path-details">
          {step.description&&<p>{step.description}</p>}
          {step.prerequisite&&<p><strong>Before you start:</strong> {step.prerequisite}</p>}
          {step.practice_task&&<div className="study-practice-task"><strong>Try it</strong><p>{step.practice_task}</p></div>}
        </div>}
        <button type="button" className="study-path-complete" onClick={()=>setCompleted(old=>({...old,[index]:!old[index]}))}>{completed[index]?'Undo completion':'Mark step complete'}</button>
      </div>
    </li>)}</ol>
    {steps.length>0&&completeCount===steps.length&&<div className="study-score-card"><span className="study-score-value">✓</span><div><b>Learning path complete!</b><p>You finished every step. Great work.</p></div></div>}
  </section>;
}