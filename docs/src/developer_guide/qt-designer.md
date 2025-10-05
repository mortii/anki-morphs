# Qt Designer

Creating dialogs with Qt Designer can make the process much easier than doing it by hand. Install it into the virtual
environment:

```bash
source venv/bin/activate
python -m pip install pyqt6 pyqt6-tools
```
Start Qt Designer with the command:
```bash
./designer-venv/lib/python3.13/site-packages/qt6_applications/Qt/bin/designer
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

```bash
pyuic6 -o ankimorphs/ui/spacy_manager_dialog_ui.py ankimorphs/ui/spacy_manager_dialog.ui
```

Useful guides:
- https://realpython.com/qt-designer-python/
- https://www.pythontutorial.net/pyqt/qt-designer/



