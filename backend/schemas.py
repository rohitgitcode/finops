from pydantic import BaseModel, Field

class ReviewRequest(BaseModel):
    """Payload schema for human-in-the-loop review actions."""
    action: str = Field(..., description="Review action: strictly APPROVE or REJECT")
    notes: str = Field(default="", description="Manager justification or override notes")

