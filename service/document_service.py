import io
import re
import uuid
from pathlib import Path
from langchain_core.documents import Document
from pypdf import PdfReader
from docx import Document as DocxDocument
from pptx import Presentation

ALLOWED={'.pdf','.docx','.pptx','.txt','.md'}

class DocumentService:
    def extract_text(self, filename: str, raw: bytes):
        ext=Path(filename).suffix.lower()
        if ext not in ALLOWED:
            raise ValueError('Supported formats: PDF, DOCX, PPTX, TXT and Markdown.')
        if len(raw)>20*1024*1024:
            raise ValueError('File exceeds 20 MB limit.')
        pages=[]
        if ext=='.pdf':
            reader=PdfReader(io.BytesIO(raw))
            for i,page in enumerate(reader.pages):
                pages.append((i+1,page.extract_text() or ''))
        elif ext=='.docx':
            doc=DocxDocument(io.BytesIO(raw))
            pages=[(1,'\n'.join(p.text for p in doc.paragraphs))]
            for ti,table in enumerate(doc.tables):
                pages.append((ti+2,'\n'.join(' | '.join(cell.text for cell in row.cells) for row in table.rows)))
        elif ext=='.pptx':
            prs=Presentation(io.BytesIO(raw))
            for i,slide in enumerate(prs.slides):
                texts=[]
                for shape in slide.shapes:
                    if hasattr(shape,'text') and shape.text.strip():
                        texts.append(shape.text)
                    if getattr(shape,'has_table',False):
                        texts.extend(' | '.join(cell.text for cell in row.cells) for row in shape.table.rows)
                pages.append((i+1,'\n'.join(texts)))
        else:
            pages=[(1,raw.decode('utf-8-sig',errors='replace'))]
        return [(number,text.strip()) for number,text in pages if text.strip()]

    def chunk(self, doc_id, pages, chunk_chars=1200, overlap=180):
        docs=[]
        for page,text in pages:
            text=re.sub(r'\s+',' ',text).strip()
            start=0
            while start<len(text):
                chunk=text[start:start+chunk_chars]
                if chunk.strip():
                    docs.append(Document(page_content='passage: '+chunk,metadata={'video_id':doc_id,'document_id':doc_id,'page':page,'chunk_index':len(docs),'source_type':'document'}))
                if start+chunk_chars>=len(text):
                    break
                start+=chunk_chars-overlap
        return docs

    def new_id(self):
        return 'doc_'+uuid.uuid4().hex
