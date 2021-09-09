TAG=$(cat source/api/api_main/settings.py | grep "VERSION" | cut -d ":" -f 2 | tr -d \' | tr -d " " | tr -d ",")
docker build ./source -t bemcom/django-api:$TAG
