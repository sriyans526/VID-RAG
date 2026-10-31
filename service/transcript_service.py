import re
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi

class TranscriptService:
    def extract_video_id(self, value):
        value=value.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}",value): return value
        match=re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})",value)
        if not match: raise ValueError("Enter a valid YouTube video ID or URL.")
        return match.group(1)

    def get_video_transcript(self, video_id, languages=None):
        api=YouTubeTranscriptApi()
        result=api.fetch(video_id,languages=languages or ["en","hi","es","fr","de","pt","ar","zh-Hans","ja","mr"])
        items=[]
        for row in result:
            text=getattr(row,"text","").strip()
            start=float(getattr(row,"start",0))
            duration=float(getattr(row,"duration",0))
            if text: items.append({"text":text,"start":start,"end":start+duration})
        if not items: raise ValueError("No transcript was available for this video.")
        return items

    def transcript_to_documents(self, transcript, video_id, chunk_words=180, overlap_words=30):
        words=[]
        for seg in transcript:
            words.extend((w,seg["start"],seg["end"]) for w in seg["text"].split())
        docs=[]; start=0
        while start<len(words):
            window=words[start:start+chunk_words]
            docs.append(Document(page_content="passage: "+" ".join(x[0] for x in window),
              metadata={"video_id":video_id,"start_time":float(window[0][1]),
                        "end_time":float(window[-1][2]),"chunk_index":len(docs)}))
            if start+chunk_words>=len(words): break
            start+=max(1,chunk_words-overlap_words)
        return docs
