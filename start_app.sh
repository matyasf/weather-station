#!/usr/bin/env bash
echo Starting radio
#sleep 10 # wait a bit for WIFI
source ./myenv/bin/activate
# 2>&1 means to redirect stderr to stdout, so both are written to the log
# -u means that the outputs are unbuffered
python -u main.py >> /home/hudejo/CODE/weather-station/log.txt 2>&1