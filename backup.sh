#!/bin/bash

TIMESTAMP=`/bin/date +%Y-%m-%d_%H:%M:%S`
/bin/mkdir -p backup
bash manage.sh dumpdata --natural-foreign --format yaml -o backup/$TIMESTAMP.yaml -e auth.Permission -e sessions -e admin.logentry --exclude contenttypes
