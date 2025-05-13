from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4


app = FastAPI()
notes_db = {}

# Pydantic model for a note
class NoteCreate(BaseModel):
    title: str = Field(..., example="Meeting Notes")
    content: str = Field(..., example="Discussed timelines and deliverables.")
    tags: List[str] = Field(default_factory=list, example=["meeting", "project", "timeline"])
    linked_note_ids: List[str] = Field(default_factory=list, example=["note-id-123"])

class Note(NoteCreate):
    id: str

class NoteDetails(Note):
    linked_notes: List[Note] = []
    backlinks: List[Note] = []

class LinkRequest(BaseModel):
    target_note_id: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    linked_note_ids: Optional[List[str]] = None


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/notes/", response_model=Note, status_code=201)
def create_note(note: NoteCreate):
    note_id = str(uuid4())
    new_note = Note(id=note_id, **note.dict())
    notes_db[note_id] = new_note
    return new_note

@app.get("/getnotes/", response_model=List[Note])
def get_notes(tag: Optional[str] = Query(None), keyword: Optional[str] = Query(None)):
    results = list(notes_db.values())

    if tag:
        results = [note for note in results if tag in note.tags]

    if keyword:
        keyword_lower = keyword.lower()
        results = [
            note for note in results
            if keyword_lower in note.title.lower() or keyword_lower in note.content.lower()
        ]

    return results

@app.get("/notes/{note_id}", response_model=NoteDetails)
def get_note_details(note_id: str):
    note = notes_db.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Get linked notes
    linked_notes = [notes_db[nid] for nid in note.linked_note_ids if nid in notes_db]

    # Get backlinks (other notes that link to this one)
    backlinks = [
        n for n in notes_db.values()
        if note_id in n.linked_note_ids
    ]

    return NoteDetails(**note.dict(), linked_notes=linked_notes, backlinks=backlinks)

# @app.patch("/notes/{note_id}/link", response_model=Note)
# def link_notes(note_id: str, link: LinkRequest):
#     source_note = notes_db.get(note_id)
#     target_note = notes_db.get(link.target_note_id)

#     if not source_note:
#         raise HTTPException(status_code=404, detail="Source note not found")
#     if not target_note:
#         raise HTTPException(status_code=404, detail="Target note not found")

#     if link.target_note_id not in source_note.linked_note_ids:
#         source_note.linked_note_ids.append(link.target_note_id)

#     return source_note


@app.patch("/notes/{note_id}", response_model=Note)
def update_note(note_id: str, update: NoteUpdate):
    note = notes_db.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = update.dict(exclude_unset=True)

    # Validate linked note IDs if they're being updated
    if "linked_note_ids" in update_data:
        for target_id in update_data["linked_note_ids"]:
            if target_id not in notes_db:
                raise HTTPException(status_code=404, detail=f"Linked note {target_id} not found")

    for field, value in update_data.items():
        setattr(note, field, value)

    return note
