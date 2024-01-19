import csv
import os
from functools import partial
from pathlib import Path
from typing import Optional

from anki.collection import Collection
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QFileDialog, QMainWindow  # pylint:disable=no-name-in-module

from . import spacy_wrapper
from .exceptions import CancelledOperationException, EmptyFileSelectionException
from .generator_dialog import GeneratorDialog
from .morpheme import Morpheme, MorphOccurrence
from .morphemizer import Morphemizer, SpacyMorphemizer
from .ui.frequency_file_generator_ui import Ui_FrequencyFileGeneratorDialog


class FrequencyFileGeneratorDialog(GeneratorDialog):
    # The UI comes from ankimorphs/ui/frequency_file_generator.ui which is used in Qt Designer,
    # which is then converted to ankimorphs/ui/frequency_file_generator_ui.py,
    # which is then imported here.
    #
    # Here we make the final adjustments that can't be made (or are hard to make) in
    # Qt Designer, like setting up tables and widget-connections.

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(child=self.__class__.__name__)
        self._output_file: str = ""
        self._setup_output_path()
        self._setup_buttons()
        self.show()

    def _setup_output_path(self) -> None:
        assert mw is not None
        assert isinstance(self.ui, Ui_FrequencyFileGeneratorDialog)

        self._output_file = os.path.join(
            mw.pm.profileFolder(), "frequency-files", "frequency.csv"
        )
        # create the parent directories if they don't exist
        Path(self._output_file).parent.mkdir(parents=True, exist_ok=True)
        self.ui.outputFileLineEdit.setText(self._output_file)

    #
    def _setup_buttons(self) -> None:
        assert isinstance(self.ui, Ui_FrequencyFileGeneratorDialog)
        self.ui.inputButton.clicked.connect(self._on_input_button_clicked)
        self.ui.outputButton.clicked.connect(self._on_output_button_clicked)
        self.ui.createFrequencyFileButton.clicked.connect(self._generate_frequency_file)

    def _on_output_button_clicked(self) -> None:
        assert mw is not None
        assert isinstance(self.ui, Ui_FrequencyFileGeneratorDialog)

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
            success=self._on_success,
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _background_generate_frequency_file(  # pylint:disable=too-many-locals
        self, col: Collection
    ) -> None:
        del col  # unused
        assert mw is not None
        assert isinstance(self.ui, Ui_FrequencyFileGeneratorDialog)

        if (
            self.ui.inputDirLineEdit.text() == ""
            or self.ui.outputFileLineEdit.text() == ""
        ):
            raise EmptyFileSelectionException

        input_files: list[Path] = self._gather_input_files()
        morph_frequency_dict: dict[str, MorphOccurrence] = {}
        nlp = None  # spacy.Language
        morphemizer: Morphemizer = self._morphemizers[self.ui.comboBox.currentIndex()]
        assert morphemizer is not None

        if isinstance(morphemizer, SpacyMorphemizer):
            selected: str = self.ui.comboBox.itemText(self.ui.comboBox.currentIndex())
            spacy_model = selected.removeprefix("spaCy: ")
            nlp = spacy_wrapper.get_nlp(spacy_model)

        for input_file in input_files:
            if mw.progress.want_cancel():  # user clicked 'x'
                raise CancelledOperationException

            mw.taskman.run_on_main(
                partial(
                    mw.progress.update,
                    label=f"Reading file: <br>{input_file.relative_to(self._input_dir_root)}",
                )
            )

            with open(input_file, encoding="utf-8") as file:
                # NB! Never use readlines(), it loads the entire file to memory
                for counter, line in enumerate(file):
                    print(f"line: {counter}")
                    morphs: list[Morpheme] = self._get_morphs_from_line(
                        morphemizer, nlp, line
                    )
                    for morph in morphs:
                        key = morph.lemma + morph.inflection
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

    #
    def _output_to_file(
        self, sorted_morph_frequency: dict[str, MorphOccurrence]
    ) -> None:
        assert isinstance(self.ui, Ui_FrequencyFileGeneratorDialog)
        output_file: str = self.ui.outputFileLineEdit.text()

        with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
            morph_writer = csv.writer(csvfile)
            morph_writer.writerow(["Morph-lemma", "Morph-inflection"])
            for morph_occurrence in sorted_morph_frequency.values():
                if morph_occurrence.occurrence < self.ui.minOccurrenceSpinBox.value():
                    break
                morph = morph_occurrence.morph
                morph_writer.writerow([morph.lemma, morph.inflection])
