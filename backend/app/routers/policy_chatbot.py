"""HTTP endpoints for the isolated hospital-policy chatbot."""

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.policy_ingestion_service import DEFAULT_POLICY_DOCUMENTS_DIR, ingest_policy_documents
from app.services.policy_rag_service import generate_policy_answer, retrieve_relevant_policy_chunks


class PolicyChatRequest(BaseModel):
    question: str = Field(min_length=1)


class PolicyChatResponse(BaseModel):
    answer: str
    citations: list[dict] = Field(default_factory=list)


class PolicyUploadResponse(BaseModel):
    uploaded_documents: list[str]
    chunks_ingested: int


router = APIRouter(tags=["Hospital Policy Chatbot"])


@router.post("/api/v1/policy-chat", response_model=PolicyChatResponse)
def policy_chat(request: PolicyChatRequest) -> PolicyChatResponse:
    matches = retrieve_relevant_policy_chunks(request.question)
    return PolicyChatResponse(
        answer=generate_policy_answer(request.question),
        citations=[
            {
                "document_id": match.chunk.source_document_id,
                "section_heading": (match.chunk.metadata_json or {}).get("section_heading"),
                "section": (match.chunk.metadata_json or {}).get("section_heading"),
                "source_url": (
                    "/api/v1/policy-chat/source/"
                    + quote(match.chunk.source_document_id, safe="")
                ),
            }
            for match in matches
        ],
    )


@router.get("/api/v1/policy-chat/source/{filename}", include_in_schema=False)
def get_policy_source(filename: str) -> FileResponse:
    """Serve only an ingested policy file as the citation target."""
    documents_dir = Path(DEFAULT_POLICY_DOCUMENTS_DIR).resolve()
    source_path = (documents_dir / Path(filename).name).resolve()
    if source_path.parent != documents_dir or source_path.suffix.lower() not in {".md", ".txt"}:
        raise HTTPException(status_code=404, detail="Policy source not found.")
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Policy source not found.")
    return FileResponse(
        source_path,
        media_type="text/plain; charset=utf-8",
        content_disposition_type="inline",
    )


@router.post(
    "/api/v1/policy-chat/upload",
    response_model=PolicyUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_policy_documents(
    files: list[UploadFile] = File(..., description="Markdown or text policy documents"),
) -> PolicyUploadResponse:
    """Store policy files in the policy-only directory and rebuild its index."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one policy document is required.")

    uploaded_documents: list[str] = []
    documents_dir = Path(DEFAULT_POLICY_DOCUMENTS_DIR)
    documents_dir.mkdir(parents=True, exist_ok=True)
    for uploaded_file in files:
        filename = Path(uploaded_file.filename or "").name
        if not filename or Path(filename).suffix.lower() not in {".md", ".txt"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported policy file '{uploaded_file.filename}'. Upload .md or .txt files.",
            )
        content = await uploaded_file.read()
        if not content.strip():
            raise HTTPException(status_code=400, detail=f"Policy file '{filename}' is empty.")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=400, detail=f"Policy file '{filename}' must be UTF-8 text.") from error
        (documents_dir / filename).write_text(text, encoding="utf-8")
        uploaded_documents.append(filename)

    return PolicyUploadResponse(
        uploaded_documents=uploaded_documents,
        chunks_ingested=ingest_policy_documents(documents_dir),
    )
