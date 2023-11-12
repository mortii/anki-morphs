from typing import Optional
from pathlib import Path, PurePath
import csv

from aqt import mw
from aqt.qt import QDialog, QMainWindow, QFileDialog  # pylint:disable=no-name-in-module
from aqt.utils import tooltip
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
            files += Path(file_path).name + " "

        self.ui.lineEdit.insert(files)
        self.path = Path(input_files[0][0]).parent
        tooltip("clicked select input button", parent=mw)

    def _on_output_button_clicked(self) -> None:
        output_file = QFileDialog.getSaveFileName(None, "Save File", "", "(*.csv)")
        print(output_file)
        self.ui.lineEdit_2.insert(output_file[0])
        tooltip("clicked select output button", parent=mw)

    def _generate_freqyency_file(self) -> None:
        field_content = self.ui.lineEdit.text()
        text = self._read_files(field_content)
        if not text:
            return
        am_config = AnkiMorphsConfig()
        morphemizer = self._morphemizers[self.ui.comboBox.currentIndex()]
        assert morphemizer is not None
        morphs = get_morphemes(morphemizer, text, am_config)
        frequency_list = self._generate_frequency_list(morphs)
        if not self.ui.lineEdit_2.text():
            tooltip("Output field is empty", parent=mw)
            return
        with open(self.ui.lineEdit_2.text(), mode='w', encoding="utf-8", newline='') as csvfile:
            spamwriter = csv.writer(csvfile)
            for [inflected, base, _] in frequency_list:
                spamwriter.writerow([inflected, base])
        tooltip("clicked create frequency file button", parent=mw)

    def _read_files(self, field_content: str) -> Optional[str]:
        if field_content == "":
            tooltip("Input field empty", parent=mw)
            return None
        if Path(field_content).is_file():
            with open(field_content, mode="r", encoding="utf-8") as file:
                return file.read()
        else:
            for file in field_content.split():
                file_path = self.path.joinpath(file)
                if not Path(file_path).is_file():
                    tooltip(str(file_path) + " dosen't exist", parent=mw)
                    return None
                with open(file_path, mode="r", encoding="utf-8") as file:
                    return file.read()

    def _generate_frequency_list(self, morphes: list[Morpheme]) -> list[[str, str, int]]:
        hash_map = {}
        for morph in morphes:
            if hash_map.get(morph.inflected) is None:
                hash_map.update({morph.inflected: [morph.base, 0]})
            else:
                occurences = hash_map.get(morph.inflected)[1]
                hash_map.update({morph.inflected: [morph.base, occurences+1]})
        result = []
        for [inflected, [base, occurences]] in hash_map.items():
            result.append([inflected, base, occurences])
        result.sort(reverse=True, key=lambda e: e[2])
        return result
