#!/bin/bash
export MYSQL_HOST=gateway01.ap-southeast-1.prod.aws.tidbcloud.com
export MYSQL_USER=3Jm9drT9RPP2wrC.root
export MYSQL_PASSWORD=A1AKFfTfuuqIXRaB
export MYSQL_DB=test
export MYSQL_PORT=4000
export MYSQL_SSL_CA=/etc/ssl/cert.pem
export PORT=5001
export HMAC_SECRET=change-this-to-a-strong-secret

venv/bin/python app.py
