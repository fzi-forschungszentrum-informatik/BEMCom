set -e
python3 /bemcom/code/manage.py makemigrations
python3 /bemcom/code/manage.py migrate
pytest /bemcom/code/
python3 /bemcom/code/manage.py runserver 0.0.0.0:8000

