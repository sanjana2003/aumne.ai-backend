from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pydantic import BaseModel
from .database import Base

# Association table for note links
note_links = Table(
    'note_links',
    Base.metadata,
    Column('source_note_id', Integer, ForeignKey('notes.id'), primary_key=True),
    Column('target_note_id', Integer, ForeignKey('notes.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

class Note(Base):
    __tablename__ = 'notes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Links relationship
    linked_notes = relationship(
        'Note',
        secondary=note_links,
        primaryjoin='Note.id==note_links.c.source_note_id',
        secondaryjoin='Note.id==note_links.c.target_note_id',
        backref='linked_by'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'linked_notes': [{'id': note.id, 'title': note.title} for note in self.linked_notes]
        }

# Pydantic models for API
class NoteBase(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []

class NoteCreate(NoteBase):
    pass

class NoteUpdate(NoteBase):
    pass

class NoteResponse(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime
    linked_notes: List[dict] = []

    class Config:
        from_attributes = True 