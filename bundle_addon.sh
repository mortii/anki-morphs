#!/bin/sh

cd ankimorphs || { echo "cd failed"; exit 1; }

# If DEV_MODE = True, set it to False
found_dev_mode=$(grep -cE "DEV_MODE: bool = (True|False)" ankimorphs_constants.py)
[ "$found_dev_mode" -eq 1 ] || { echo "grep result was not 1!"; exit 1; }
sed -i 's/DEV_MODE: bool = True/DEV_MODE: bool = False/g' ankimorphs_constants.py

# Find and store the AnkiMorphs version number. Will be used in .addon file name
version="v$(grep -Po '(?<=version: )[^\"]*' settings_dialog.py)"
version=$(echo "$version" | tr . -)  # replace . with - for filename to work

# all pycache files have to be deleted before we can zip the .addon file
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete

# meta.json is the local user's customized version of config.json, don't bundle this.
rm meta.json

zip -r ../ankimorphs-"$version".ankiaddon ./*

cd ..
