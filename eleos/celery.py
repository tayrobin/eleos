from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
#from celery.schedules import crontab

#import eleos_core.slack_views

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eleos.settings')

app = Celery('eleos')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


#@app.on_after_configure.connect
#def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    #sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')

    # Calls test('world') every 30 seconds
    #sender.add_periodic_task(30.0, test.s('world'), expires=10)

    # Executes every Monday morning at 7:30 a.m.
    #sender.add_periodic_task(
    #    crontab(hour=7, minute=30, day_of_week=1),
    #    test.s('Happy Mondays!'),
    #)

    # test with my own modules
    #sender.add_periodic_task(
    #	crontab(hour=8, minute=30),
    #	eleos_core.slack_views.sendTextToSlack.s('Good Morning from Celery!', 'moment_builder'),
    #	name='Daily Slack Message'
    #)