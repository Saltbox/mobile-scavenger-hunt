import os

DEBUG = os.environ.get('DEBUG')
SECRET_KEY = os.environ.get('SECRET_KEY')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')

WAX_LOGIN = os.environ.get('WAX_LOGIN')
WAX_PASSWORD = os.environ.get('WAX_PASSWORD')
WAX_SITE = os.environ.get('WAX_SITE')

SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
