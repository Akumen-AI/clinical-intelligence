from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from app.models.user import User
from app.services.rag.rbac_access_guard import RbacAccessGuard, AccessDeniedError


class RagCitation(BaseModel):
    document_id: str
    snippet: str
    location: Optional[str] = None


class RagAnswer(BaseModel):
    answer: str
    citations: List[RagCitation] = []
    source_documents: List[dict] = []


class PatientRagService:
    async def query(self, patient_id: UUID, question: str, user: User) -> RagAnswer:
        RbacAccessGuard().assert_can_query_patient(user, patient_id)

        from app.services.rag_service import generate_answer
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            answer_text, citations_list = generate_answer(db, str(patient_id), question)
            citations_objs = [
                RagCitation(
                    document_id=c.get("document_id", ""),
                    snippet=c.get("snippet", ""),
                    location=c.get("location"),
                )
                for c in citations_list
            ]
            return RagAnswer(
                answer=answer_text,
                citations=citations_objs,
                source_documents=citations_list,
            )
        finally:
            db.close()


def get_patient_rag_service() -> PatientRagService:
    return PatientRagService()
