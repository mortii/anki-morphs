# Setup

## Linux

1. Set up local environment:  
   You need to have python version 3.9 or higher.
    ``` bash
    python3 -m virtualenv venv
    source venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```
2. Set the project python interpreter to be `MorphMan/venv/bin/python3.{xx}` to get your IDE to recognize the packages
   installed above.

3. Create a soft symbolic link from the cloned repo to the anki add-ons folder so anki finds morphman:
   ``` bash
   ln -s path/to/cloned/repo/MorphMan/morph  ~/.local/share/Anki2/addons21/morph
   ```
4. The bash shell script `.githooks/pre-commit` contains commands that check for errors in the project:
   ``` bash
   pytest  # uses pytest.ini
   export PYTHONPATH=./  # necessary to run pylint on tests-directory
   pylint tests morph -d W0611
   ```

   You can run these commands in a terminal manually if you want, or you can set the script up to run automatically before commits by running `scripts/setup_dev.sh`. Alternatively, you
   can create a run configuration in your IDE to execute the script, that way you can easily run it at your convenience.






