#!/bin/sh

cd ankimorphs || { echo "cd failed"; exit 1; }
version="v$(grep -Po '(?<=version: )[^\"]*' settings_dialog.py)"
version=$(echo "$version" | tr . -)  # replace . with - for filename to work
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
rm meta.json
zip -r ../ankimorphs-"$version".ankiaddon ./*
cd ..