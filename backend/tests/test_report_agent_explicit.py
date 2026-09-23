import pytest
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.document import Document, DocumentStatus
from app.services.nl_report_service import generate_report, run_structured_query
import uuid

@pytest.fixture
def agent_test_data(db_session):
    u = User(id=uuid.uuid4(), email="doc_agent@test", role="doctor", patient_access=["p-100"])
    u2 = User(id=uuid.uuid4(), email="dept_head@test", role="department_head", department_access=["Cardiology"])
    
    p1 = Patient(patient_id="p-100", name="Auth Patient")
    p2 = Patient(patient_id="p-200", name="Unauth Patient")
    
    db_session.add_all([u, u2, p1, p2])
    
    d1 = Document(document_id="doc-100", patient_id="p-100", filename="doc1.pdf", raw_uri="s3://test/doc1.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value)
    d2 = Document(document_id="doc-200", patient_id="p-200", filename="doc2.pdf", raw_uri="s3://test/doc2.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value)
    db_session.add_all([d1, d2])
    
    v1 = Visit(visit_id=str(uuid.uuid4()), patient_id="p-100", document_id="doc-100", department="Cardiology")
    v2 = Visit(visit_id=str(uuid.uuid4()), patient_id="p-200", document_id="doc-200", department="Cardiology")
    db_session.add_all([v1, v2])
    
    db_session.commit()
    return {"doc": u, "dept_head": u2}

def test_run_structured_query_enforces_rbac_for_doctor(db_session, agent_test_data):
    doc = agent_test_data["doc"]
    
    # Doctor asks for all patients in Cardiology
    filters = {"department": "Cardiology"}
    data = run_structured_query(db_session, filters, current_user=doc)
    
    # Should only return 1 count (for p-100), because p-200 is not in their access
    assert len(data) == 1
    assert data[0]["label"] == "Cardiology"
    assert data[0]["count"] == 1

def test_run_structured_query_enforces_rbac_for_dept_head(db_session, agent_test_data):
    dept_head = agent_test_data["dept_head"]
    
    # Head asks for all patients in Cardiology (allowed)
    filters = {"department": "Cardiology"}
    data = run_structured_query(db_session, filters, current_user=dept_head)
    
    # Should return both patients (count = 2)
    assert len(data) == 1
    assert data[0]["label"] == "Cardiology"
    assert data[0]["count"] == 2
    
    # Head asks for patients in Neurology (not allowed)
    filters = {"department": "Neurology"}
    data = run_structured_query(db_session, filters, current_user=dept_head)
    assert len(data) == 0

def test_generate_report_returns_query_plan(db_session, agent_test_data):
    doc = agent_test_data["doc"]
    
    # "Show me admissions in Cardiology"
    res = generate_report(db_session, "Show me admissions in Cardiology", current_user=doc)
    
    assert "query_plan" in res
    plan = res["query_plan"]
    assert plan["department_scope"] == "Cardiology"
    assert plan["cohort"] == "Authorized Patients Only"
