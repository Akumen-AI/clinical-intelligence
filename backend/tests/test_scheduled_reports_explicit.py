import pytest
import uuid
from datetime import datetime, timedelta
from app.models.user import User
from app.models.scheduled_report import ScheduledReport
from app.tasks.report_tasks import _execute_single_report

def test_run_scheduled_report_success(db_session, tmp_path):
    user_id_obj = uuid.uuid4()
    user_id = str(user_id_obj)
    u = User(id=user_id_obj, email="schedule@test", role="hospital_admin")
    db_session.add(u)
    db_session.flush()

    report_id = str(uuid.uuid4())
    report_def = {
        "filters": {"department": "Cardiology"},
        "chart_type": "bar"
    }
    sr = ScheduledReport(
        id=report_id,
        user_id=user_id,
        report_definition=report_def,
        schedule="0 * * * *",
        output_format="pdf",
        destination="s3://bucket/test"
    )
    db_session.add(sr)
    db_session.commit()

    now = datetime.utcnow()
    
    # Run the report
    _execute_single_report(db_session, sr, now)

    # Check that it updated its next_run_at and last_run_at
    db_session.refresh(sr)
    assert sr.last_run_at == now
    assert sr.next_run_at is not None
    assert sr.next_run_at > now
    assert sr.failure_state is None
