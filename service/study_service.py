import json
import re

class StudyService:
    def __init__(self,llm):
        self.llm=llm

    def generate(self,kind,source_text,count=8,difficulty='medium',language='auto'):
        specs={
            'quiz':'Create multiple-choice quiz questions. Return JSON array of objects with question, options (4 strings), answer_index (0-3), explanation, and evidence_quote.',
            'flashcards':'Create study flashcards. Return JSON array of objects with front, back, and evidence_quote.',
            'summary':'Create structured study notes. Return JSON object with title, summary, key_points array, definitions array of {term,definition}, and revision_questions array.',
            'mindmap':'Create a hierarchical mind map. Return JSON object with central_topic and branches array of {topic,children:[strings]}.',
            'learning_path':'Create a learning path. Return JSON object with goal and steps array of {title,description,prerequisite,practice_task}.'
        }
        if kind not in specs:
            raise ValueError('Unsupported study material type.')
        prompt=(f"You are a careful educator. Use ONLY this source material; do not invent facts. "
                f"Language: {language}. Difficulty: {difficulty}. Generate exactly {count} concise items. "
                f"{specs[kind]} Keep explanations and evidence quotes brief. Return valid JSON only, "
                f"with no markdown or reasoning. Source:\n{source_text[:8000]}")
        response=self.llm.invoke(prompt)
        text=getattr(response,'content',str(response))
        if isinstance(text,list):
            text=''.join(str(x.get('text','')) if isinstance(x,dict) else str(x) for x in text)
        text=re.sub(r'^```(?:json)?\s*|\s*```$','',str(text).strip(),flags=re.I)
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            match=re.search(r'(\[.*\]|\{.*\})',text,re.S)
            if match:
                try:
                    result = json.loads(match.group(1))
                except json.JSONDecodeError:
                    raise ValueError('The model did not return valid JSON. Please retry.')
            else:
                raise ValueError('The model did not return valid JSON. Please retry.')
        if isinstance(result, list):
            return result[:count]
        return result
