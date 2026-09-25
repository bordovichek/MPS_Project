FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --system --create-home app \
    && mkdir -p staticfiles media \
    && chown -R app:app /app \
    && chmod +x docker-entrypoint.sh

EXPOSE 8000

# Стартуем от root только ради chown томов — entrypoint сразу переключается на пользователя app.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "MPS_Project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
