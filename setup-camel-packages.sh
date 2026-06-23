#!/usr/bin/env bash

echo "Installing CAMeL Tools..."
python -m pip install camel-tools==1.6.0

CAMEL_DATABASES=(
  calima-msa-r13
  calima-egy-r13
  calima-glf-01
)

db_to_package () {
  case "$1" in
    calima-msa-r13) echo "morphology-db-msa-r13" ;;
    calima-egy-r13) echo "morphology-db-egy-r13" ;;
    calima-glf-01) echo "morphology-db-glf-01" ;;
  esac
}

echo "Installing CAMeL morphology databases..."

for m in "${CAMEL_DATABASES[@]}"; do
  package=$(db_to_package "$m")
  python -m camel_tools.cli.camel_data --install "$package"
done

echo "Done installing CAMeL resources."
