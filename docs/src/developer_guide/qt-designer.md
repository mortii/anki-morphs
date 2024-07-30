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

Convert ui file to python:
```bash
pyuic6 -o ankimorphs/ui/settings_dialog_ui.py ankimorphs/ui/settings_dialog.ui
```
```bash
pyuic6 -o ankimorphs/ui/tag_selection_dialog_ui.py ankimorphs/ui/tag_selection_dialog.ui
```
```bash
pyuic6 -o ankimorphs/ui/generators_window_ui.py ankimorphs/ui/generators_window.ui
```
```bash
pyuic6 -o ankimorphs/ui/known_morphs_exporter_dialog_ui.py ankimorphs/ui/known_morphs_exporter_dialog.ui
```
```bash
pyuic6 -o ankimorphs/ui/view_morphs_dialog_ui.py ankimorphs/ui/view_morphs_dialog.ui
```
```bash
pyuic6 -o ankimorphs/ui/generator_output_dialog_ui.py ankimorphs/ui/generator_output_dialog.ui
```
```bash
pyuic6 -o ankimorphs/ui/progression_window_ui.py ankimorphs/ui/progression_window.ui
```

Useful guides:
- https://realpython.com/qt-designer-python/
- https://www.pythontutorial.net/pyqt/qt-designer/



