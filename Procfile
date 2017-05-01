web: newrelic-admin run-program gunicorn eleos.wsgi --log-file -
worker: newrelic-admin run-program celery worker --app=eleos -E --loglevel=info