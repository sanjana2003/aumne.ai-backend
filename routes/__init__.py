from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uvicorn

from models.database import engine, get_db
from models.note import Note, NoteCreate, NoteUpdate, NoteResponse, Base
from models import note_links

def register_routes(app: Flask):
    """Register all blueprints/routes with the app"""
    app.register_blueprint(notes_bp) 