from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from uuid import uuid4

app = FastAPI()

# In-memory storage for demo purposes
notes_db = {}

# Pydantic model for a note
class NoteCreate(BaseModel):
    title: str = Field(..., example="Meeting Notes")
    content: str = Field(..., example="Discussed timelines and deliverables.")
    tags: List[str] = Field(default_factory=list, example=["meeting", "project", "timeline"])

class Note(NoteCreate):
    id: str

@app.post("/notes/", response_model=Note, status_code=201)
def create_note(note: NoteCreate):
    note_id = str(uuid4())
    new_note = Note(id=note_id, **note.dict())
    notes_db[note_id] = new_note
    return new_note
