#!/bin/bash

/wait-for-it.sh rabbitmq:5672 -- /wait-for-it.sh odoo:8069 -- python data_processor.py
