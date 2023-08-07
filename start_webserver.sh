#!/bin/bash

cd ~/DMScreen/; gunicorn --workers 1 --timeout 180 -b :8000 webserver:app &
gunicorn --workers 1 -b :4242 stripe_webhook:app &
