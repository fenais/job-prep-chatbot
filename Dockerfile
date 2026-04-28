FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate
RUN python manage.py seed_starter_content
RUN python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')"
CMD ["gunicorn", "jobprepchatbot.wsgi:application", "--bind", "0.0.0.0:8080"]
