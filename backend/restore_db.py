from app.database import engine
from app.db.base import Base

# Create all tables (including the new patient_rag_chunks)
Base.metadata.create_all(bind=engine)
print("Database recreated.")
