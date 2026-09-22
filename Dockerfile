FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate
RUN python manage.py seed_starter_content
# Creates an admin account only when DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD are set in the deploy environment
CMD python manage.py createsuperuser --noinput 2>/dev/null; gunicorn jobprepchatbot.wsgi:application --bind 0.0.0.0:8080
