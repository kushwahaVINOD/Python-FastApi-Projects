from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import datetime


app = FastAPI(
    title="Audit Log Service",
    description="API for managing user audit logs",
    version="1.0.0"
)


# In-memory storage for audit logs
audit_logs_db = []


class ActionLogBase(BaseModel):
    action: str
    message: str
    status: Optional[str] = "success"


class ActionLogCreate(ActionLogBase):
    pass


class AuditLogEntry(ActionLogBase):
    id: str
    timestamp: datetime.datetime
    user_id: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Audit Log Service API", "version": "1.0.0"}


@app.post("/audit-logs")
async def create_audit_log(action_log: ActionLogCreate):
    """
    Create and publish an audit log entry
    
    This endpoint accepts action details and publishes the audit log.
    Returns the created audit log entry.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    
    # Generate unique ID
    new_id = str(uuid.uuid4())
    
    # Create audit log entry
    audit_entry = AuditLogEntry(
        id=new_id,
        action=action_log.action,
        message=action_log.message,
        status=action_log.status or "success",
        timestamp=timestamp,
        user_id=None  # Can be added later for specific user tracking
    )
    
    # Add to in-memory database
    audit_logs_db.append(audit_entry)
    
    print(f"✓ Audit Log Created: {audit_entry.action} | Message: {audit_entry.message}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Status: {audit_entry.status}")
    print("────────────────────────────")
    
    return audit_entry


@app.get("/audit-logs", response_model=list[AuditLogEntry], tags=["audit"])
async def get_audit_logs(limit: int = 50):
    """
    Get audit logs (paginated)
    
    - **limit**: Maximum number of logs to return (default: 50)
    """
    if limit < 0:
        raise HTTPException(status_code=400, detail="Limit must be non-negative")
    
    # Return recent logs (most recent first)
    recent_logs = audit_logs_db[-limit:] if len(audit_logs_db) > limit else audit_logs_db.copy()
    recent_logs.reverse()  # Oldest first
    
    print(f"✓ Retrieved {len(recent_logs)} audit log(s)")
    
    return recent_logs


@app.get("/audit-logs/{log_id}", response_model=AuditLogEntry, tags=["audit"])
async def get_audit_log(log_id: str):
    """
    Get a single audit log by ID
    
    - **log_id**: The unique identifier of the audit log to retrieve
    """
    # Find the log in the database
    for log in audit_logs_db:
        if log.id == log_id:
            print(f"✓ Retrieved audit log: {log_id}")
            return log
    
    raise HTTPException(status_code=404, detail="Audit log not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
