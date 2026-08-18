from app.core.security import User
import uuid
u = User(id=uuid.uuid4())
print("User ID:", u.id, type(u.id))
