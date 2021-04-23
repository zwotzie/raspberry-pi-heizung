#!/usr/bin/env bash

sudo supervisorctl stop heizung

python RelaisStatus.py 
