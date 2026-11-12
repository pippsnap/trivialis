"""Punkte und Rangliste.

Die Punkte werden aus den gespeicherten Antworten (UserAnswer) berechnet:
Jede Szene zählt nur einmal – beim ersten richtigen Lösen. Wie viele
Punkte es gibt, hängt davon ab, im wievielten Versuch die Szene gelöst wurde.
"""
from datetime import datetime

from app import db
from app.models import Answer, Story, Task, User, UserAnswer

# Punkte je nach Versuch: 1. Versuch richtig = 10, 2. Versuch = 5, danach = 2
POINTS_BY_ATTEMPT = {1: 10, 2: 5}
POINTS_LATER = 2


def points_for_attempt(attempt):
    return POINTS_BY_ATTEMPT.get(attempt, POINTS_LATER)


def _solves(user_id=None):
    """Liefert pro (Kind, Szene) die erste richtige Lösung: Zeitpunkt und Punkte."""
    q = (db.session.query(UserAnswer.user_id, UserAnswer.task_id, UserAnswer.created_at, Answer.is_correct)
         .join(Answer, UserAnswer.answer_id == Answer.id))
    if user_id is not None:
        q = q.filter(UserAnswer.user_id == user_id)
    rows = q.order_by(UserAnswer.user_id, UserAnswer.task_id, UserAnswer.created_at, UserAnswer.id).all()

    attempts, solves = {}, {}
    for uid, tid, created_at, is_correct in rows:
        key = (uid, tid)
        if key in solves:
            continue  # Szene schon gelöst – spätere Antworten zählen nicht
        attempts[key] = attempts.get(key, 0) + 1
        if is_correct:
            solves[key] = {'user_id': uid, 'task_id': tid, 'at': created_at,
                           'points': points_for_attempt(attempts[key])}
    return solves


def user_points(user_id):
    return sum(s['points'] for s in _solves(user_id).values())


def task_points(user_id, task_id):
    """Punkte, die das Kind für diese Szene bekommen hat (0, falls noch nicht gelöst)."""
    s = _solves(user_id).get((user_id, task_id))
    return s['points'] if s else 0


def scoreboard(event_limit=12):
    solves = _solves()
    tasks = {t.id: t for t in Task.query.all()}
    stories = {s.id: s for s in Story.query.filter_by(is_active=True)}
    tasks_per_story = {}
    for t in tasks.values():
        tasks_per_story.setdefault(t.storyId, set()).add(t.id)

    # Alle mit Punkten erscheinen; Lehrpersonen/Admins bekommen ein Label
    kids = {u.id: u for u in User.query.all()}

    def label(user):
        names = {r.name for r in user.roles}
        if 'Admin' in names:
            return 'Admin'
        if 'Teacher' in names:
            return 'Lehrperson'
        return None

    players = {}
    for s in solves.values():
        if s['user_id'] not in kids or s['task_id'] not in tasks:
            continue
        p = players.setdefault(s['user_id'], {'points': 0, 'solved': set(), 'last': s['at']})
        p['points'] += s['points']
        p['solved'].add(s['task_id'])
        p['last'] = max(p['last'], s['at'])

    rows = []
    for uid, p in players.items():
        done = sum(1 for sid, ids in tasks_per_story.items() if sid in stories and ids and ids <= p['solved'])
        rows.append({'id': uid, 'name': kids[uid].username, 'label': label(kids[uid]), 'points': p['points'],
                     'scenes': len(p['solved']), 'stories': done, '_last': p['last']})
    # Bei Gleichstand gewinnt, wer die Punkte früher erreicht hat (wie bei einem CTF)
    rows.sort(key=lambda r: (-r['points'], r['_last']))
    for i, r in enumerate(rows):
        r['rank'] = i + 1
        del r['_last']

    now = datetime.utcnow()
    events = []
    for s in sorted(solves.values(), key=lambda s: s['at'], reverse=True):
        if s['user_id'] not in kids or s['task_id'] not in tasks:
            continue
        t = tasks[s['task_id']]
        story = stories.get(t.storyId)
        events.append({'name': kids[s['user_id']].username, 'scene': t.name,
                       'story': story.name if story else '', 'points': s['points'],
                       'seconds_ago': max(0, int((now - s['at']).total_seconds()))})
        if len(events) >= event_limit:
            break

    return {'players': rows, 'events': events,
            'total_scenes': sum(len(ids) for sid, ids in tasks_per_story.items() if sid in stories),
            'total_stories': len(stories)}
