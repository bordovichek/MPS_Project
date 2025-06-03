FROM python:3.12
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE MPS_Project.settings
WORKDIR /app
COPY requiremets.txt /app/
RUN pip install --no-cache-dir -r requiremets.txt
COPY . /app/
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["/app/gunicorn_start.sh"]