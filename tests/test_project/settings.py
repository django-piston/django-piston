import os
DEBUG = True
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/piston.db'
INSTALLED_APPS = (
    'django.contrib.auth', 
    'django.contrib.contenttypes', 
    'django.contrib.sessions', 
    'piston',
    'test_project.apps.testapp',
)
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)
ROOT_URLCONF = 'test_project.urls'

MIDDLEWARE_CLASSES = (
    'piston.middleware.ConditionalMiddlewareCompatProxy',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'piston.middleware.CommonMiddlewareCompatProxy',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
