import os

DEBUG = os.environ.get('DEBUG')
SECRET_KEY = os.environ.get('SECRET_KEY')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')

SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
ASSETS_DEBUG = os.environ.get('ASSETS_DEBUG')
