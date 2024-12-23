#!/usr/bin/env bash

sudo supervisorctl stop heizung

venv/bin/python RelaisStatus.py
