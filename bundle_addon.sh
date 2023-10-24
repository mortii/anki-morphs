#!/bin/sh

cd ankimorphs || { echo "cd failed"; exit 1; }
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
rm meta.json
zip -r ../ankimorphs.ankiaddon ./*
cd ..