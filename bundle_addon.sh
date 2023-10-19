rm -rf ./.pytest_cache/ ./.mypy_cache/ ankimorphs/ankimorphs.db ankimorphs/meta.json
cd ankimorphs && zip -r ../ankimorphs.ankiaddon ./*
