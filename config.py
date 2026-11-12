import os, random, string
from flask_security.utils import uia_username_mapper

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
  # Secret key used by different plugins (ie. Flask-Security, Flask-WTF)
  SECRET_KEY = os.environ.get('SECRET_KEY', ''.join(random.choice(string.ascii_lowercase) for i in range(32)))

  # Database (Flask-SQLAlchemy): Options
  SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'mysql://admin:admin@localhost/trivialis_dev')
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  # Localization (Flask-Babel): Available Languages
  LANGUAGES = [
    {
      'name': 'English',
      'isoCode': 'en',
      'icon': 'gb'
    },
    {
      'name': 'Deutsch',
      'isoCode': 'de',
      'icon': 'de'
    }
  ]

  # Authentication (Flask-Security): Core
  USER_ROLES = [
    {
      'name': 'Admin',
      'description': 'Admin users can manage the application.',
      'permissions': {'admin-read', 'admin-write'}
    },
    {
      'name': 'Teacher',
      'description': 'Teachers can manage their tenant and enable or disable stories.',
      'permissions': {'teacher-read', 'teacher-write'}
    },
    {
      'name': 'User',
      'description': 'Users can interact with the application and configure their profile.',
      'permissions': {'user-read', 'user-write'}
    }
  ]
  SECURITY_PASSWORD_SALT = os.environ.get('PASSWORD_SALT', 'lkuibefkjbdmybcazwvefoauflbvclszydvfkahaqiuehgf')
  SECURITY_USER_IDENTITY_ATTRIBUTES = [
    {'username': {'mapper': uia_username_mapper, 'case_insensitive': True}}
  ]
  # Authentication (Flask-Security): Compatibility
  SECURITY_ANONYMOUS_USER_DISABLED = True
  # Nach Login/Logout auf die Startseite
  SECURITY_POST_LOGIN_VIEW = '/stories/'
  SECURITY_POST_LOGOUT_VIEW = '/'
  # Logout per Link (GET) erlauben
  SECURITY_LOGOUT_METHODS = ['GET', 'POST']
  # Authentication (Flask-Security): Login/Logout
  #SECURITY_LOGOUT_METHODS = ['Post']
  # Authentication (Flask-Security): Registerable
  # Kinder melden sich nur mit ihrem Vornamen auf der Startseite an (siehe main.index)
  SECURITY_REGISTERABLE = False
  SECURITY_SEND_REGISTER_EMAIL = False # Make this dependent on environment (nonprod, prod)
  SECURITY_USERNAME_ENABLE = True
  SECURITY_USERNAME_REQUIRED = True # School kids don't necessarily have an email address
  SECURITY_USERNAME_MINLENGTH = 3 # Think of short names like Ben or Tom
  SECURITY_USERNAME_MAXLENGTH = 32
  # Authentication (Flask-Security): Changeable
  SECURITY_CHANGEABLE = True
  SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False 
  # Authentication (Flask-Security): Recoverable
  SECURITY_RECOVERABLE = False
  SECURITY_SEND_PASSWORD_RESET_EMAIL = False 
