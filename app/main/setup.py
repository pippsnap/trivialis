from flask import current_app
from flask_security import hash_password

from app import db
import json
from app.models import Language, Profile, Role, Story, Task, Answer, UserAnswer, Resource

#Function to create languages
def create_languages(): 
  for l in current_app.config['LANGUAGES']:
    db.session.add(Language(name=l['name'], isoCode=l['isoCode'], icon=l['icon']))
  db.session.commit()
  return True

#Function to create roles
def create_roles():
  for r in current_app.config['USER_ROLES']:
    current_app.security.datastore.find_or_create_role(
      name = r['name'],
      description = r['description'],
      permissions = r['permissions']
    )
  db.session.commit()
  return True

#Function to create users
def create_users(adminUsername, adminEmail, adminPassword, adminLanguage):
  for r in Role.query.all():
    if r.name == 'Admin':
      current_app.security.datastore.create_user(
        email = adminEmail,
        username = adminUsername,
        password = hash_password(adminPassword),
        roles = ['Admin']
      )
      # Override admin language with selected language
      db.session.commit()
      adminProfile = Profile.query.first()
      adminProfile.languageId = adminLanguage
    else:
      current_app.security.datastore.create_user(
        email = r.name+'@salerva.ch',
        username = r.name,
        password = hash_password(r.name+'123'),
        roles = [r.name]
      )
  db.session.commit()
  return True

#Function to create stories (Cybersecurity-Geschichten für den Zukunftstag)
def create_stories():
  from .content import STORIES
  # Bestehende Geschichten inkl. Szenen, Antworten und Fortschritt entfernen
  UserAnswer.query.delete()
  Resource.query.delete()
  Answer.query.delete()
  Task.query.delete()
  Story.query.delete()
  db.session.commit()

  german = Language.query.filter_by(isoCode='de').first()
  for s in STORIES:
    story = Story(languageId=german.id if german else None, name=s['name'], description=s['description'], is_active=True)
    db.session.add(story)
    db.session.flush()
    for i, scene in enumerate(s['scenes']):
      task = Task(storyId=story.id, sort=i, type='multiple_choice', points=0,
                  name=scene['title'], read_text=scene['text'],
                  description=scene['question'], correct_text=scene['lesson'])
      db.session.add(task)
      db.session.flush()
      if scene.get('visual'):
        # Bild zur Szene (SMS, Chat, Pop-up, ...) als JSON speichern
        db.session.add(Resource(task_id=task.id, name='visual', description=json.dumps(scene['visual'], ensure_ascii=False)))
      for j, (text, is_correct, explanation) in enumerate(scene['answers']):
        db.session.add(Answer(task_id=task.id, text=text, is_correct=is_correct, description=explanation, sort_order=j))
  db.session.commit()
  return Story.query.all()

# Kept for compatibility: tasks are created together with the stories
def create_tasks():
  return Task.query.all()
