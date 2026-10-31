from service.transcript_service import TranscriptService
from service.vector_service import VectorService

class IngestionService:
    def __init__(self):
        self.transcript_service=TranscriptService()
        self.vector_service=VectorService()
    def ingest_video(self, video_value, languages=None, force=False):
        video_id=self.transcript_service.extract_video_id(video_value)
        if self.vector_service.has_video(video_id) and not force:
            return {"video_id":video_id,"status":"already_processed","chunks":0}
        transcript=self.transcript_service.get_video_transcript(video_id,languages)
        docs=self.transcript_service.transcript_to_documents(transcript,video_id)
        count=self.vector_service.add_documents(docs,replace=force)
        return {"video_id":video_id,"status":"processed","chunks":count,"transcript_segments":len(transcript)}
