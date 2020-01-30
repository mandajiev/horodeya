TIMESTAMP=`date +%Y-%m-%d_%H:%M:%S`
mkdir -p backup
./manage.sh dumpdata --natural-foreign --format yaml -o backup/$TIMESTAMP.yaml -e auth.Permission -e sessions -e admin.logentry --exclude contenttypes
