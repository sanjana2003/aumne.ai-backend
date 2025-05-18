from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import sqlite3
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE = "zettelkasten.db"  # Changed to match the same database used in initialize_database

# ----------- Database Setup -----------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------- Models -----------

class NoteCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]
    backlinks: List[str]
    links: List[str]

class LinkCreate(BaseModel):
    target_title: str

# ----------- Helper Functions -----------

def normalize_tags(tags):
    return list(set(tag.lower().strip() for tag in tags))

def resolve_links(content):
    return re.findall(r"\[\[([^\]]+)\]\]", content)

def insert_tags(conn, note_id, tags):
    for tag in tags:
        tag = tag.lower().strip()
        tag_id = conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,)).lastrowid
        if not tag_id:
            tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO note_tags(note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))

def insert_links(conn, source_id, linked_titles):
    for title in linked_titles:
        row = conn.execute("SELECT id FROM notes WHERE title = ?", (title,)).fetchone()
        if row and row["id"] != source_id:
            try:
                conn.execute("INSERT OR IGNORE INTO links(source_id, target_id) VALUES (?, ?)", 
                            (source_id, row["id"]))
            except sqlite3.OperationalError:
                conn.execute("INSERT OR IGNORE INTO links(from_note_id, to_note_id) VALUES (?, ?)", 
                            (source_id, row["id"]))

def initialize_database():
    conn = sqlite3.connect(DATABASE)  # Use the same DATABASE constant
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            source_id INTEGER,  
            target_id INTEGER, 
            PRIMARY KEY (source_id, target_id),
            FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

# ----------- Endpoints -----------

@app.post("/notes/")
def create_note(note: NoteCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO notes(title, content) VALUES (?, ?)", (note.title, note.content))
        note_id = cursor.lastrowid
        insert_tags(conn, note_id, note.tags)
        linked_titles = resolve_links(note.content)
        insert_links(conn, note_id, linked_titles)
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Note with this title already exists.")
    return {"message": "Note created successfully."}

@app.get("/notes/", response_model=List[NoteOut])
def get_notes(tag: Optional[str] = None, keyword: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM notes"
    args = []
    if tag:
        query = '''SELECT n.* FROM notes n
                   JOIN note_tags nt ON n.id = nt.note_id
                   JOIN tags t ON t.id = nt.tag_id
                   WHERE t.name = ?'''
        args = [tag.lower()]
    elif keyword:
        query += " WHERE title LIKE ? OR content LIKE ?"
        args = [f"%{keyword}%", f"%{keyword}%"]

    rows = cursor.execute(query, args).fetchall()
    result = []
    for row in rows:
        note_id = row["id"]
        tags = [r[0] for r in cursor.execute("""
            SELECT name FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            WHERE nt.note_id = ?""", (note_id,))]
        
        # Check which column names exist in the links table
        try:
            links = [r[0] for r in cursor.execute("""
                SELECT n2.title FROM links
                JOIN notes n2 ON n2.id = links.target_id
                WHERE links.source_id = ?""", (note_id,))]
            backlinks = [r[0] for r in cursor.execute("""
                SELECT n1.title FROM links
                JOIN notes n1 ON n1.id = links.source_id
                WHERE links.target_id = ?""", (note_id,))]
        except sqlite3.OperationalError:
            # Fall back to the old column names if the new ones don't exist
            links = [r[0] for r in cursor.execute("""
                SELECT n2.title FROM links
                JOIN notes n2 ON n2.id = links.to_note_id
                WHERE links.from_note_id = ?""", (note_id,))]
            backlinks = [r[0] for r in cursor.execute("""
                SELECT n1.title FROM links
                JOIN notes n1 ON n1.id = links.from_note_id
                WHERE links.to_note_id = ?""", (note_id,))]

        result.append(NoteOut(id=note_id, title=row["title"], content=row["content"], tags=tags, links=links, backlinks=backlinks))
    return result

@app.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int):
    conn = get_db()
    cursor = conn.cursor()
    note = cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    tags = [r[0] for r in cursor.execute("SELECT t.name FROM tags t JOIN note_tags nt ON t.id = nt.tag_id WHERE nt.note_id = ?", (note_id,))]
    
    # Check which column names exist in the links table
    try:
        links = [r[0] for r in cursor.execute("""
            SELECT n2.title FROM links
            JOIN notes n2 ON n2.id = links.target_id
            WHERE links.source_id = ?""", (note_id,))]
        backlinks = [r[0] for r in cursor.execute("""
            SELECT n1.title FROM links
            JOIN notes n1 ON n1.id = links.source_id
            WHERE links.target_id = ?""", (note_id,))]
    except sqlite3.OperationalError:
        # Fall back to the old column names if the new ones don't exist
        links = [r[0] for r in cursor.execute("""
            SELECT n2.title FROM links
            JOIN notes n2 ON n2.id = links.to_note_id
            WHERE links.from_note_id = ?""", (note_id,))]
        backlinks = [r[0] for r in cursor.execute("""
            SELECT n1.title FROM links
            JOIN notes n1 ON n1.id = links.from_note_id
            WHERE links.to_note_id = ?""", (note_id,))]
            
    return NoteOut(id=note["id"], title=note["title"], content=note["content"], tags=tags, links=links, backlinks=backlinks)

@app.patch("/notes/{note_id}/link")
def create_link(note_id: int, link: LinkCreate):
    conn = get_db()
    cursor = conn.cursor()
    source = cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    target = cursor.execute("SELECT * FROM notes WHERE title = ?", (link.target_title,)).fetchone()

    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target note not found")
    if source["id"] == target["id"]:
        raise HTTPException(status_code=400, detail="Cannot link note to itself")

    # Try both column name patterns to handle existing database structures
    try:
        cursor.execute("INSERT OR IGNORE INTO links(source_id, target_id) VALUES (?, ?)", 
                      (source["id"], target["id"]))
    except sqlite3.OperationalError:
        cursor.execute("INSERT OR IGNORE INTO links(from_note_id, to_note_id) VALUES (?, ?)", 
                      (source["id"], target["id"]))
                      
    conn.commit()
    return {"message": "Link created successfully"}

@app.get("/graph/")
def get_graph():
    conn = get_db()
    cursor = conn.cursor()
    
    # Try both schema versions
    try:
        edges = cursor.execute("""
            SELECT n1.title as source, n2.title as target
            FROM links
            JOIN notes n1 ON n1.id = links.source_id
            JOIN notes n2 ON n2.id = links.target_id
        """).fetchall()
    except sqlite3.OperationalError:
        edges = cursor.execute("""
            SELECT n1.title as source, n2.title as target
            FROM links
            JOIN notes n1 ON n1.id = links.from_note_id
            JOIN notes n2 ON n2.id = links.to_note_id
        """).fetchall()
        
    graph = {}
    for edge in edges:
        graph.setdefault(edge["source"], []).append(edge["target"])
    return graph

if __name__ == "__main__":
    import uvicorn
    initialize_database()
    uvicorn.run(app, host="127.0.0.1", port=8000)
else:
    initialize_database()
