# Qt Designer

Creating dialogs with Qt Designer can make the process much easier than doing it by hand. The Qt Designer packages
conflicts with the anki-qt (aqt), so we need to use a different virtual environment.

```bash
python3.9 -m pip install --upgrade pip
python3.9 -m pip install virtualenv
python3.9 -m virtualenv designer-venv
source designer-venv/bin/activate
python3.9 -m pip install pyqt6 pyqt6-tools
```
Start Qt Designer with the command:
```bash
./designer-venv/lib/python3.9/site-packages/qt6_applications/Qt/bin/designer
```


https://www.pythontutorial.net/pyqt/qt-designer/

https://realpython.com/qt-designer-python/

https://www.pythonguis.com/tutorials/pyqt6-first-steps-qt-designer/