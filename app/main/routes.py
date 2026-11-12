import secrets
from flask import flash, redirect, render_template, request, url_for, current_app
from flask_babel import _
from flask_security import current_user, hash_password, login_user

from app import db
from app.forms import RegisterSchoolForm, SetupForm
from app.main import bp
from app.models import Language, School, User, Story  # Stellen Sie sicher, dass das Story-Modell importiert wird
from .content import STORIES
from .setup import create_languages, create_roles, create_stories, create_tasks, create_users

#Startseite: Kinder melden sich nur mit ihrem Vornamen an
@bp.route('/', methods=['GET', 'POST'])
def index():
  # Redirect to setup page if no users are in database
  if not User.query.first():
    return redirect(url_for('main.setup'), code=307)

  error = None
  if request.method == 'POST':
    name = ' '.join(request.form.get('name', '').split())[:32]
    if len(name) < 2:
      error = 'Bitte gib deinen Vornamen ein (mindestens 2 Buchstaben).'
    else:
      user = User.query.filter(db.func.lower(User.username) == name.lower()).first()
      if user and (user.has_role('Admin') or user.has_role('Teacher')):
        # Konten von Lehrpersonen/Admins brauchen ein Passwort
        return redirect(url_for('security.login'))
      if user and not user.active:
        error = 'Dieser Name ist gesperrt. Bitte frag die Lehrperson.'
      else:
        if not user:
          user = current_app.security.datastore.create_user(
            username=name,
            email=f'{secrets.token_hex(8)}@zukunftstag.invalid',
            password=hash_password(secrets.token_urlsafe(16)),
            roles=['User'],
          )
          db.session.commit()
        login_user(user, remember=True)
        db.session.commit()
        return redirect(url_for('story.stories'))

  return render_template('main/index.html', error=error, topics=STORIES)

#Route for Setup
@bp.route('/setup/', methods=['GET', 'POST'])
def setup():
  # Redirect to homepage if one or more users are already in the database
  users = User.query.all()
  if users:
    return redirect(url_for('main.index'))
  if not Language.query.all():
    # No languages are defined in database
    create_languages()
  form = SetupForm()
  choices = [(l.id, l.name) for l in Language.query.all()]
  form.adminLanguage.choices = choices
  form.websiteLanguage.choices = choices
  if form.validate_on_submit():
    # Set websites default language with selected language
    websiteLanguage = Language.query.filter_by(id=form.websiteLanguage.data).first()
    websiteLanguage.isDefault = True
    db.session.commit()
    # Create default roles and users from config
    create_roles()
    create_users(form.username.data, form.email.data, form.password.data, form.adminLanguage.data)
    create_stories()
    create_tasks()
    flash(_('Successfully setup website.'))
    return redirect(url_for('main.index'))
  return render_template('main/setup.html', form=form)
