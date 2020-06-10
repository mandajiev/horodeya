## Настройка на средата за разработка

```bash
virtualenv venv
source venv/bin/activate
pip install Django
```

### Локална база данни

```bash
docker run --name horodeya-postgres -e POSTGRES_USER=horodeya -e POSTGRES_PASSWORD=horodeya -d postgres
```

След като сме пуснали postgres Docker изображението:

```bash
export DB_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' horodeya-postgres)
export DB_URL="postgresql://horodeya:horodeya@$DB_HOST/horodeya"
```

### Стартиране

```bash
manage.py migrate
manage.py loaddata fixtures/dev.yaml
```

### Превод

```bash
manage.py makemessages -l bg -i venv/bin
```

После редактирай преводите в `locale` и `locale-allauth`. Накрая компилирай преводите:

```bash
manage.py compilemessages -l bg
```

### Запазване на локална информация

```bash
./manage.sh dumpdata --natural-foreign --format yaml -o fixtures/dev.yaml -e auth.Permission -e sessions -e admin.logentry --exclude contenttypes
```
