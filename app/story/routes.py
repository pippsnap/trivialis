import json
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_security import auth_required, current_user, roles_required
from app.story import bp
from app.models import Story, Task, Answer, UserAnswer
from app.main.content import STORIES
from app import db
from .scoring import scoreboard, task_points, user_points

# Titelbild (Icon, Emoji, Farbe) pro Geschichte, nach Name der Geschichte
DEFAULT_COVER = {'icon': 'bi-shield-lock', 'color': '#1d4ed8'}
STORY_COVERS = {s['name']: {k: s.get(k, v) for k, v in DEFAULT_COVER.items()} for s in STORIES}


def cover(story):
    return STORY_COVERS.get(story.name, DEFAULT_COVER)


def visual(task):
    res = task.resource
    if res and res.name == 'visual' and res.description:
        try:
            return json.loads(res.description)
        except ValueError:
            return None
    return None


def solved_task_ids(user_id):
    """IDs aller Szenen, die das Kind richtig beantwortet hat."""
    rows = (db.session.query(UserAnswer.task_id)
            .join(Answer, UserAnswer.answer_id == Answer.id)
            .filter(UserAnswer.user_id == user_id, Answer.is_correct.is_(True))
            .distinct().all())
    return {r[0] for r in rows}


#Übersicht aller Geschichten
@bp.route('/')
@auth_required()
def stories():
    stories = Story.query.filter_by(is_active=True).order_by(Story.id).all()
    solved = solved_task_ids(current_user.id)
    done = set()
    for story in stories:
        task_ids = {t.id for t in Task.query.filter_by(storyId=story.id)}
        if task_ids and task_ids <= solved:
            done.add(story.id)
    return render_template('story/geschichten.html', stories=stories, done=done, cover=cover)


#Eine Geschichte Szene für Szene spielen
@bp.route('/<int:story_id>')
@auth_required()
def story(story_id):
    story = Story.query.filter_by(id=story_id, is_active=True).first_or_404()
    tasks = Task.query.filter_by(storyId=story.id).order_by(Task.sort, Task.id).all()
    scenes = [{
        'id': t.id,
        'title': t.name,
        'text': t.read_text or '',
        'question': t.description or '',
        'visual': visual(t),
        'lesson': t.correct_text or '',
        'answers': [{
            'id': a.id,
            'text': a.text,
            'correct': bool(a.is_correct),
            'explanation': a.description or '',
        } for a in t.answers.order_by(Answer.sort_order, Answer.id)],
    } for t in tasks]
    return render_template('story/geschichte.html', story=story, scenes=scenes,
                           cover=cover(story))


#Antwort speichern (für die "Geschafft"-Markierung in der Übersicht)
@bp.route('/<int:story_id>/task/<int:task_id>/answer', methods=['POST'])
@auth_required()
def answer_question(story_id, task_id):
    task = Task.query.filter_by(id=task_id, storyId=story_id).first_or_404()
    data = request.get_json(silent=True) or request.form
    answer = Answer.query.filter_by(id=data.get('answer'), task_id=task.id).first()
    if not answer:
        return jsonify({'ok': False}), 400
    already = task_points(current_user.id, task.id)
    db.session.add(UserAnswer(user_id=current_user.id, task_id=task.id, answer_id=answer.id, points_earned=0))
    db.session.commit()
    # Punkte gibt es nur beim ersten Lösen einer Szene
    gained = 0 if already else task_points(current_user.id, task.id)
    return jsonify({'ok': True, 'correct': bool(answer.is_correct),
                    'points': gained, 'total': user_points(current_user.id)})


#Druckbare Urkunde "Internet-Detektiv"
@bp.route('/urkunde')
@auth_required()
def certificate():
    from datetime import date
    stories = Story.query.filter_by(is_active=True).order_by(Story.id).all()
    solved = solved_task_ids(current_user.id)
    done = [s for s in stories
            if (ids := {t.id for t in Task.query.filter_by(storyId=s.id)}) and ids <= solved]
    return render_template('story/urkunde.html', done=done, total=len(stories),
                           today=date.today().strftime('%d.%m.%Y'), cover=cover)


#Live-Rangliste (z. B. für den Beamer)
@bp.route('/rangliste')
@auth_required()
def leaderboard():
    return render_template('story/rangliste.html')


#Daten für die Live-Rangliste (wird alle paar Sekunden neu geladen)
@bp.route('/rangliste/daten')
@auth_required()
def leaderboard_data():
    data = scoreboard()
    data['me'] = current_user.id
    response = jsonify(data)
    response.headers['Cache-Control'] = 'no-store'
    return response


#Rangliste zurücksetzen (nur Admin), z. B. zwischen zwei Gruppen
@bp.route('/rangliste/zuruecksetzen', methods=['POST'])
@roles_required('Admin')
def leaderboard_reset():
    UserAnswer.query.delete()
    db.session.commit()
    flash('Die Rangliste wurde zurückgesetzt.')
    return redirect(url_for('story.leaderboard'))
