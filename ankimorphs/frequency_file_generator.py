from typing import Optional
from pathlib import Path, PurePath
import csv
from typing import Any, Union

from anki.collection import Collection
from aqt import mw
from aqt.qt import QDialog, QMainWindow, QFileDialog  # pylint:disable=no-name-in-module
from aqt.utils import tooltip
from aqt.operations import QueryOp
from .morph_utils import get_morphemes
from .config import AnkiMorphsConfig
from .morpheme import Morpheme


from .morphemizer import Morphemizer, get_all_morphemizers, get_morphemizer_by_name
from .ui.frequency_file_generator_ui import Ui_FrequencyFileGeneratorDialog


def main() -> None:
    mw.ankimorphs_frequency_file_generator = FrequencyFileGeneratorDialog(mw)  # type: ignore[union-attr]
    mw.ankimorphs_frequency_file_generator.exec()  # type: ignore[union-attr]


class FrequencyFileGeneratorDialog(QDialog):
    # The UI comes from ankimorphs/ui/frequency_file_generator.ui which is used in Qt Designer,
    # which is then converted to ankimorphs/ui/frequency_file_generator_ui.py,
    # which is then imported here.
    #
    # Here we make the final adjustments that can't be made (or are hard to make) in
    # Qt Designer, like setting up tables and widget-connections.

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        assert mw
        self.mw = parent  # pylint:disable=invalid-name
        self.ui = Ui_FrequencyFileGeneratorDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self._morphemizers = get_all_morphemizers()
        self._populate_morphemizers()
        self._setup_buttons()
        self.path = PurePath("")

    def _populate_morphemizers(self) -> None:
        morphemizers: list[Morphemizer] = get_all_morphemizers()
        morphemizer_names = [mizer.get_description() for mizer in morphemizers]
        morphemizers_cbox = self.ui.comboBox
        morphemizers_cbox.addItems(morphemizer_names)

    def _setup_buttons(self) -> None:
        self.ui.inputButton.clicked.connect(self._on_input_button_clicked)
        self.ui.outputButton.clicked.connect(self._on_output_button_clicked)
        self.ui.createFrequencyFileButton.clicked.connect(self._generate_freqyency_file)

    def _on_input_button_clicked(self) -> None:
        input_files = QFileDialog.getOpenFileNames(None, "Files to Analyze", "", "(*.txt *.srt)")
        files = ""
        if not input_files[0]:
            return
        for file_path in input_files[0]:
            files += Path(file_path).name + ","
        self.ui.lineEdit.setText(files)
        self.path = Path(input_files[0][0]).parent

    def _on_output_button_clicked(self) -> None:
        profile_path: str = mw.pm.profileFolder()
        output_file = QFileDialog.getSaveFileName(None, "Save File", profile_path, "CSV File (*.csv)")
        self.ui.lineEdit_2.setText(output_file[0])

    def _generate_freqyency_file(self) -> None:
        assert mw is not None

        mw.progress.start(label="Generating frequency list")

        operation = QueryOp(
            parent=mw,
            op=self._background_generate_frequency_file,
            success=on_success,
        )
        operation.with_progress().run_in_background()

    def _read_files(self, field_content: str) -> Optional[str]:
        if field_content == "":
            tooltip("Input field empty", parent=mw)
            return None
        files = field_content.split(",")
        if len(files) == 1 and Path(field_content).is_file():
            file_path = Path(field_content)
            with file_path.open() as file:
                return file.read()
        else:
            for file in files:
                file_path = self.path.joinpath(file)
                if not Path(file_path).is_file():
                    tooltip(str(file_path) + " dosen't exist", parent=mw)
                    return None
                with file_path.open() as file:
                    return file.read()

    def _generate_frequency_list(self, morphes: list[Morpheme]) -> list[[str, str, int]]:
        morph_occurrence_dict = {}
        for morph in morphes:
            if morph_occurrence_dict.get(morph.inflected) is None:
                morph_occurrence_dict.update({morph.inflected: [morph.base, 0]})
            else:
                occurences = morph_occurrence_dict.get(morph.inflected)[1]
                morph_occurrence_dict.update({morph.inflected: [morph.base, occurences+1]})
        result = []
        for [inflected, [base, occurences]] in morph_occurrence_dict.items():
            result.append([inflected, base, occurences])
        result.sort(reverse=True, key=lambda e: e[2])
        return result

    def _background_generate_frequency_file(self, col: Collection) -> None:
        del col
        field_content = self.ui.lineEdit.text()
        text = self._read_files(field_content)
        if not text:
            return
        if not self.ui.lineEdit_2.text():
            tooltip("Output field is empty", parent=mw)
            return
        am_config = AnkiMorphsConfig()
        morphemizer = self._morphemizers[self.ui.comboBox.currentIndex()]
        assert morphemizer is not None
        morphs = get_morphemes(morphemizer, text, am_config)
        frequency_list = self._generate_frequency_list(morphs)
        with open(self.ui.lineEdit_2.text(), mode='w+', encoding="utf-8", newline='') as csvfile:
            spamwriter = csv.writer(csvfile)
            for [inflected, base, _] in frequency_list:
                spamwriter.writerow([inflected, base])


def on_success(result: Any) -> None:
    # This function runs on the main thread.
    del result  # unused
    assert mw is not None
    assert mw.progress is not None
    global start_time

    mw.toolbar.draw()  # updates stats
    mw.progress.finish()
    tooltip("Frequency list generated", parent=mw)


def on_failure(
    error: Any,
) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()
    tooltip("Frequency list generation failed")