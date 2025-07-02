#!/bin/bash
cd /var/www/kampuslu
source venv/bin/activate

# Python path'i temizle
unset PYTHONPATH
export PYTHONPATH=/var/www/kampuslu
export DJANGO_SETTINGS_MODULE=core.settings

# Daphne'yi başlat
exec venv/bin/daphne -b 127.0.0.1 -p 8001 core.asgi:application