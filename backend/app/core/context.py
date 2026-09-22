import contextvars
import uuid

# Context variables to hold correlation_id and actor_id across async contexts
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

actor_id_ctx: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "actor_id", default=None
)

def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()

def set_correlation_id(correlation_id: str) -> contextvars.Token:
    return correlation_id_ctx.set(correlation_id)

def get_actor_id() -> uuid.UUID | None:
    return actor_id_ctx.get()

def set_actor_id(actor_id: uuid.UUID) -> contextvars.Token:
    return actor_id_ctx.set(actor_id)
