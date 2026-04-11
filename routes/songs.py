from flask import Blueprint, request, jsonify
from db import get_db_connection

songs_bp = Blueprint('songs', __name__)


@songs_bp.route('/api/songs', methods=['GET'])
def get_songs():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, artist, album, genre FROM SongDetails ORDER BY title")
            songs = cur.fetchall()
    finally:
        conn.close()
    return jsonify(songs=songs)


@songs_bp.route('/api/songs/<int:song_id>', methods=['GET'])
def get_song(song_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, artist, album, genre FROM SongDetails WHERE id = %s", (song_id,))
            song = cur.fetchone()
            if not song:
                return jsonify(error='Song not found.'), 404
            cur.execute("SELECT id, songPart, lyrics FROM SongLyrics WHERE songId = %s ORDER BY id", (song_id,))
            lyrics = cur.fetchall()
            cur.execute("SELECT * FROM FontSettings WHERE songId = %s LIMIT 1", (song_id,))
            settings = cur.fetchone()
    finally:
        conn.close()
    return jsonify(song=song, lyrics=lyrics, settings=settings)


@songs_bp.route('/api/songs', methods=['POST'])
def create_song():
    data = request.get_json()
    title = (data.get('title') or '').strip()
    artist = (data.get('artist') or '').strip()
    album = (data.get('album') or '').strip()
    genre = (data.get('genre') or '').strip()
    lyrics = data.get('lyrics', [])
    settings = data.get('settings', {})

    if not title:
        return jsonify(success=False, error='Title is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO SongDetails (title, artist, album, genre) VALUES (%s, %s, %s, %s)",
                (title, artist, album, genre)
            )
            song_id = cur.lastrowid

            for lyric in lyrics:
                cur.execute(
                    "INSERT INTO SongLyrics (songId, songPart, lyrics) VALUES (%s, %s, %s)",
                    (song_id, lyric.get('songPart', ''), lyric.get('lyrics', ''))
                )

            if settings:
                cur.execute("""
                    INSERT INTO FontSettings
                        (songId, fontSize, color, weight, family, outline, shadow, textcase, alignment, bgType, bgImage, formattingJson)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    song_id,
                    settings.get('fontSize'), settings.get('color'), settings.get('weight'),
                    settings.get('family'), settings.get('outline'), settings.get('shadow'),
                    settings.get('textcase'), settings.get('alignment'), settings.get('bgType'),
                    settings.get('bgImage'), settings.get('formattingJson')
                ))
        conn.commit()
    finally:
        conn.close()
    return jsonify(success=True, id=song_id)


@songs_bp.route('/api/songs/<int:song_id>', methods=['PUT'])
def update_song(song_id):
    data = request.get_json()
    title = (data.get('title') or '').strip()
    artist = (data.get('artist') or '').strip()
    album = (data.get('album') or '').strip()
    genre = (data.get('genre') or '').strip()
    lyrics = data.get('lyrics', [])
    settings = data.get('settings', {})

    if not title:
        return jsonify(success=False, error='Title is required.'), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE SongDetails SET title=%s, artist=%s, album=%s, genre=%s WHERE id=%s",
                (title, artist, album, genre, song_id)
            )
            cur.execute("DELETE FROM SongLyrics WHERE songId = %s", (song_id,))
            for lyric in lyrics:
                cur.execute(
                    "INSERT INTO SongLyrics (songId, songPart, lyrics) VALUES (%s, %s, %s)",
                    (song_id, lyric.get('songPart', ''), lyric.get('lyrics', ''))
                )

            if settings:
                cur.execute("SELECT id FROM FontSettings WHERE songId = %s", (song_id,))
                existing = cur.fetchone()
                if existing:
                    cur.execute("""
                        UPDATE FontSettings SET fontSize=%s, color=%s, weight=%s, family=%s, outline=%s,
                        shadow=%s, textcase=%s, alignment=%s, bgType=%s, bgImage=%s, formattingJson=%s
                        WHERE songId=%s
                    """, (
                        settings.get('fontSize'), settings.get('color'), settings.get('weight'),
                        settings.get('family'), settings.get('outline'), settings.get('shadow'),
                        settings.get('textcase'), settings.get('alignment'), settings.get('bgType'),
                        settings.get('bgImage'), settings.get('formattingJson'), song_id
                    ))
                else:
                    cur.execute("""
                        INSERT INTO FontSettings
                            (songId, fontSize, color, weight, family, outline, shadow, textcase, alignment, bgType, bgImage, formattingJson)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        song_id,
                        settings.get('fontSize'), settings.get('color'), settings.get('weight'),
                        settings.get('family'), settings.get('outline'), settings.get('shadow'),
                        settings.get('textcase'), settings.get('alignment'), settings.get('bgType'),
                        settings.get('bgImage'), settings.get('formattingJson')
                    ))
        conn.commit()
    finally:
        conn.close()
    return jsonify(success=True)


@songs_bp.route('/api/songs/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM SongDetails WHERE id = %s", (song_id,))
            if not cur.fetchone():
                return jsonify(success=False, error='Song not found.'), 404
            cur.execute("DELETE FROM SongDetails WHERE id = %s", (song_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify(success=True)
