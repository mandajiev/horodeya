export DB_HOST='localhost'
export SECRET_KEY='{{secret_key}}'
export AWS_ACCESS_KEY_ID='{{aws_access_key_id}}'
export AWS_SECRET_ACCESS_KEY='{{aws_secret_access_key}}'
export AWS_DEFAULT_REGION='eu-west-1'
export ANYMAIL_WEBHOOK_SECRET='{{anymail_webhook_secret}}'

export STREAM_API_KEY='{{stream_api_key}}'
export STREAM_API_SECRET='{{stream_api_secret}}'
export DB_PASSWORD='{{db_password}}'
export DB_NAME='{{db_name}}'
export DB_USER='{{db_user}}'
export OIDC_RP_CLIENT_ID='{{oidc_client_id}}'
export OIDC_RP_CLIENT_SECRET='{{oidc_client_secret}}'

venv/bin/python manage.py $@
