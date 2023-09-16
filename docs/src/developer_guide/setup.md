# Setup

## Unix

1. Set up local environment:  
   You need to have python version 3.9 or higher. 
    ``` bash
    python3 -m virtualenv venv
    source venv/bin/activate
    python3 -m pip install aqt[qt5]==2.1.66 aqt[qt6]==2.1.66 anki==2.1.66 pylint==2.17.5 pytest==7.4.2 pytest-randomly==3.15.0 pytest-qt==4.2.0 pytest-xvfb==3.0.0
    ```
2. Set the project python interpreter to be `MorphMan/venv/bin/python3.{xx}` to get your IDE to recognize the packages
   installed above.

3. Create a soft symbolic link from the cloned repo to the anki add-ons folder so anki finds morphman:
   ``` bash
   ln -s path/to/cloned/repo/MorphMan/morph  ~/.local/share/Anki2/addons21/morph
   ```
4. The bash shell script `.githooks/pre-commit` contains commands that checks for errors in the project. You can set
   this up to run automatically before commits with `scripts/setup_dev.sh`. Another option is to create a run
   configuration in your IDE to execute the script, that way you can easily run it at your convenience, or just run it
   from a terminal

export PYTHONPATH=./  # necessary to run pylint on test-directory

