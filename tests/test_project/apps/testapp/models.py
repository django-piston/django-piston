from django.db import models

class TestModel(models.Model):
    test1 = models.CharField(max_length=1, blank=True, null=True)
    test2 = models.CharField(max_length=1, blank=True, null=True)
    pass
