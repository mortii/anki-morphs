# Qt Designer

Creating dialogs with Qt Designer is often much easier than building them by hand. Installing Qt Designer via `pip` can
cause dependency conflicts, so it's recommended to install the standalone version instead:

```bash
sudo apt install qt6-tools-dev-tools
```
Start Qt Designer with the command:
```bash
/usr/lib/qt6/bin/designer
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



