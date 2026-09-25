#!/bin/sh
set -e

# Тома, созданные прежней версией контейнера, принадлежат root: чиним владельца и сбрасываем привилегии.
if [ "$(id -u)" = "0" ]; then
    chown -R app:app /app/staticfiles /app/media
    export HOME=/home/app
    exec setpriv --reuid=app --regid=app --init-groups "$0" "$@"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput --verbosity 0

exec "$@"
