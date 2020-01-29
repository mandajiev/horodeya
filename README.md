## Настройка на средата за разработка

```
$ virtualenv venv
$ source venv/bin/activate
$ pip install Django
```

### Локална база данни

```
$ docker run --name horodeya-postgres -e POSTGRES_USER=horodeya -e POSTGRES_PASSWORD=horodeya -d postgres
```

След като сме пуснали postgres Docker изображението:

```
$ export DB_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' betrobot-postgres)
$ export DB_URL="postgresql://betrobot:betrobot@$DB_HOST/betrobot"
```

### Стартиране

```
$ manage.py migrate
$ manage.py loaddata fixtures/dev.yaml
```

### Превод

```
$ manage.py makemessages -l bg -i venv/bin
```

После редактирай преводите в `locale` и `locale-allauth`. Накрая компилирай преводите:

```
$ manage.py compilemessages -l bg
```

### Запазване на локална информация

```
./manage.sh dumpdata --natural-foreign --format yaml -o fixtures/dev.yaml -e auth.Permission -e sessions -e admin.logentry --exclude contenttypes
```
