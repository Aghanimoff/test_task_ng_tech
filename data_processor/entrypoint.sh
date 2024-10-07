#!/bin/bash
/app/wait-for-it.sh rabbitmq:5672 -- \
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client data_processor.py
