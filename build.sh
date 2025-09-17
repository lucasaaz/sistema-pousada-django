#!/usr/bin/env bash
# exit on error
set -o errexit

# ADICIONE ESTA LINHA PARA INSTALAR AS DEPENDÊNCIAS PRIMEIRO
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate