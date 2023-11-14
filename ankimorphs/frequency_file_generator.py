import csv
import os
import re
from functools import partial
from pathlib import Path
from typing import Any, Optional, Union

from anki.collection import Collection
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (  # pylint:disable=no-name-in-module
    QDialog,
    QDir,
    QFileDialog,
    QMainWindow,
)
from aqt.utils import tooltip

from .exceptions import CancelledOperationException, EmptyFileSelectionException
from .morph_utils import (
    _remove_names,
    round_brackets_regex,
    slim_round_brackets_regexp,
    square_brackets_regex,
)
from .morpheme import Morpheme
from .morphemizer import get_all_morphemizers
from .ui.frequency_file_generator_ui import Ui_FrequencyFileGeneratorDialog


class MorphOccurrence:
    __slots__ = (
        "morph",
        "occurrence",
    )

    def __init__(self, morph: Morpheme) -> None:
        self.morph: Morpheme = morph
        self.occurrence: int = 1


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
        self._output_file: str = ""
        self._setup_output_path()
        self._setup_buttons()
        self.input_files: list[str] = []

    def _populate_morphemizers(self) -> None:
        morphemizer_names = [mizer.get_description() for mizer in self._morphemizers]
        morphemizers_cbox = self.ui.comboBox
        morphemizers_cbox.addItems(morphemizer_names)

    def _setup_output_path(self) -> None:
        assert mw is not None
        self._output_file = os.path.join(
            mw.pm.profileFolder(), "frequency-files", "frequency.csv"
        )
        # create the parent directories if they don't exist
        Path(self._output_file).parent.mkdir(parents=True, exist_ok=True)
        self.ui.outputFileLineEdit.setText(self._output_file)

    def _setup_buttons(self) -> None:
        self.ui.inputButton.clicked.connect(self._on_input_button_clicked)
        self.ui.outputButton.clicked.connect(self._on_output_button_clicked)
        self.ui.createFrequencyFileButton.clicked.connect(self._generate_frequency_file)

    def _on_input_button_clicked(self) -> None:
        input_files_list: list[str] = QFileDialog.getOpenFileNames(
            None, "Files to Analyze", QDir().homePath(), "(*.txt *.srt)"
        )[0]
        self.ui.inputFileLiineEdit.setText("".join(input_files_list))
        self.input_files = input_files_list

    def _on_output_button_clicked(self) -> None:
        assert mw is not None
        output_file = QFileDialog.getSaveFileName(
            None, "Save File", self._output_file, "CSV File (*.csv)"
        )
        self.ui.outputFileLineEdit.setText(output_file[0])

    def _generate_frequency_file(self) -> None:
        assert mw is not None
        mw.progress.start(label="Generating frequency list")
        operation = QueryOp(
            parent=mw,
            op=self._background_generate_frequency_file,
            success=on_success,
        )
        operation.failure(on_failure)
        operation.with_progress().run_in_background()

    def _background_generate_frequency_file(self, col: Collection) -> None:
        del col  # unused
        assert mw is not None

        if len(self.input_files) == 0 or self.ui.outputFileLineEdit.text() == "":
            raise EmptyFileSelectionException

        morph_frequency_dict: dict[str, MorphOccurrence] = {}
        morphemizer = self._morphemizers[self.ui.comboBox.currentIndex()]
        assert morphemizer is not None

        for input_file in self.input_files:
            if mw.progress.want_cancel():  # user clicked 'x'
                raise CancelledOperationException

            mw.taskman.run_on_main(
                partial(
                    mw.progress.update,
                    label=f"Reading file:<br>{input_file}",
                )
            )

            with open(input_file, encoding="utf-8") as file:
                # NB! Never use readlines(), it loads the entire file to memory
                for line in file:
                    expression = self._filter_expression(line)
                    morphs = morphemizer.get_morphemes_from_expr(expression)
                    if self.ui.namesFileCheckBox.isChecked():
                        morphs = _remove_names(morphs)
                    for morph in morphs:
                        key = morph.norm + morph.inflected
                        if key in morph_frequency_dict:
                            morph_frequency_dict[key].occurrence += 1
                        else:
                            morph_frequency_dict[key] = MorphOccurrence(morph)

        sorted_morph_frequency = dict(
            sorted(
                morph_frequency_dict.items(),
                key=lambda item: item[1].occurrence,
                reverse=True,
            )
        )
        self._output_to_file(sorted_morph_frequency)

    def _filter_expression(self, expression: str) -> str:
        if self.ui.squareBracketsCheckBox.isChecked():
            if square_brackets_regex.search(expression):
                expression = square_brackets_regex.sub("", expression)

        if self.ui.roundBracketsCheckBox.isChecked():
            if round_brackets_regex.search(expression):
                expression = round_brackets_regex.sub("", expression)

        if self.ui.slimRoundBracketsCheckBox.isChecked():
            if slim_round_brackets_regexp.search(expression):
                expression = slim_round_brackets_regexp.sub("", expression)

        if self.ui.numbersCheckBox.isChecked():
            expression = re.sub(r"\d", "", expression)

        return expression

    def _output_to_file(
        self, sorted_morph_frequency: dict[str, MorphOccurrence]
    ) -> None:
        output_file: str = self.ui.outputFileLineEdit.text()

        with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
            morph_writer = csv.writer(csvfile)
            morph_writer.writerow(["Morph-base", "Morph-inflected"])
            for morph_occurrence in sorted_morph_frequency.values():
                if morph_occurrence.occurrence < self.ui.minOccurrenceSpinBox.value():
                    break
                morph = morph_occurrence.morph
                morph_writer.writerow([morph.norm, morph.inflected])


def on_success(result: Any) -> None:
    # This function runs on the main thread.
    del result  # unused
    assert mw is not None
    assert mw.progress is not None

    mw.toolbar.draw()  # updates stats
    mw.progress.finish()
    tooltip("Frequency list generated", parent=mw)


def on_failure(
    error: Union[
        Exception,
        CancelledOperationException,
        EmptyFileSelectionException,
    ]
) -> None:
    # This function runs on the main thread.
    assert mw is not None
    assert mw.progress is not None
    mw.progress.finish()

    if isinstance(error, CancelledOperationException):
        tooltip("Cancelled Frequency File Generator")
    if isinstance(error, EmptyFileSelectionException):
        tooltip("No file selected")
    else:
        raise error
