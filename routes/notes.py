from flask import Blueprint, request, jsonify
from models import db, Note

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/api/notes', methods=['GET'])
def get_notes():
    notes = Note.query.all()
    return jsonify([note.to_dict() for note in notes])

@notes_bp.route('/api/notes', methods=['POST'])
def create_note():
    data = request.get_json()
    note = Note(
        title=data['title'],
        content=data['content'],
        tags=','.join(data.get('tags', []))
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201

@notes_bp.route('/api/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@notes_bp.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    note = Note.query.get_or_404(note_id)
    data = request.get_json()
    
    note.title = data.get('title', note.title)
    note.content = data.get('content', note.content)
    if 'tags' in data:
        note.tags = ','.join(data['tags'])
    
    db.session.commit()
    return jsonify(note.to_dict())

@notes_bp.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return '', 204

@notes_bp.route('/api/notes/<int:note_id>/links/<int:target_id>', methods=['POST'])
def create_link(note_id, target_id):
    source_note = Note.query.get_or_404(note_id)
    target_note = Note.query.get_or_404(target_id)
    
    if target_note not in source_note.linked_notes:
        source_note.linked_notes.append(target_note)
        db.session.commit()
    
    return jsonify(source_note.to_dict()) 