#!/bin/bash
# This script downloads the WeGo GTFS for use with case_study.ipynb.
curl -A "Mozilla/5.0" -O https://www.wegotransit.com/googleexport/google_transit.zip
yes | unzip google_transit.zip
rm -r google_transit.zip
