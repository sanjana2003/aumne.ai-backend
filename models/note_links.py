from .note import db

note_links = db.Table('note_links',
    db.Column('source_note_id', db.Integer, db.ForeignKey('notes.id'), primary_key=True),
    db.Column('target_note_id', db.Integer, db.ForeignKey('notes.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=db.func.current_timestamp())
) 