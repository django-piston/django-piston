import django

if django.VERSION[:2] == (1, 2):
    from settings12 import *
else:
    from settings13 import *
