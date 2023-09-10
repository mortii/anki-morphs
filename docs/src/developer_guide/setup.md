# Setup

## Unix

1. Set up local environment:
    ``` bash
    python -m virtualenv venv  # python3
    source venv/bin/activate
    python -m pip install aqt[qt6] aqt[qt5] anki pylint mypy types-setuptools pytest  # pip3
    export PYTHONPATH=./  # necessary to run pylint on test-directory
    ```
2. Set the project python interpreter to be `MorphMan/venv/bin/python3.{xx}` to get your IDE to recognize the packages
   installed above.
3. The bash shell script `.githooks/pre-commit` contains commands that checks for errors in the project. You can set
   this up to run automatically before commits with `scripts/setup_dev.sh`. Another option is to create a run
   configuration in your IDE to execute the script, that way you can easily run it at your convenience.


