from pydantic import BaseModel, Field


class CVUploadResponse(BaseModel):
    session_id: str = Field(..., description="Unique ID for this processing session")
    filename: str
    status: str = Field(default="processing")
    message: str = Field(default="CV received and processing started")
