# Piston imports
# from models import Consumer
from utils import send_consumer_mail

def consumer_post_save(sender, instance, created, **kwargs):
    send_consumer_mail(instance)

def consumer_post_delete(sender, instance, **kwargs):
    instance.status = 'canceled'
    send_consumer_mail(instance)
