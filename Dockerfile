FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN python manage.py migrate
CMD ["gunicorn", "jobprepchatbot.wsgi:application", "--bind", "0.0.0.0:8080"]