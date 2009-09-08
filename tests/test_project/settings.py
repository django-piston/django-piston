import os
DEBUG = True
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/piston.db'
INSTALLED_APPS = (
    'django.contrib.auth', 
    'django.contrib.contenttypes', 
    'django.contrib.sessions', 
    'django.contrib.sites',
    'piston',
    'test_project.apps.testapp',
)
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

SITE_ID = 1
ROOT_URLCONF = 'test_project.urls'

MIDDLEWARE_CLASSES = (
    'piston.middleware.ConditionalMiddlewareCompatProxy',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'piston.middleware.CommonMiddlewareCompatProxy',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
