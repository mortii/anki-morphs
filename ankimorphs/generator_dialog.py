import re
from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional, Union

import aqt
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QDialog,
    QDir,
    QFileDialog,
    QMainWindow,
)
from aqt.utils import tooltip

from . import ankimorphs_globals, morphemizer, text_preprocessing
from .exceptions import (
    CancelledOperationException,
    EmptyFileSelectionException,
    SpacyNotInstalledException,
)
from .morpheme import Morpheme
from .morphemizer import Morphemizer
from .text_preprocessing import (
    remove_names_textfile,
    round_brackets_regex,
    slim_round_brackets_regexp,
    square_brackets_regex,
)
from .ui.frequency_file_generator_ui import Ui_FrequencyFileGeneratorDialog
from .ui.readability_report_generator_ui import Ui_ReadabilityReportGeneratorDialog


class GeneratorDialog(QDialog):
    # Since there is so much overlap between the frequency file generator and the
    # readability report generator, it makes sense to have them both inherit from
    # a parent class.

    def __init__(
        self,
        child: str,
        parent: Optional[QMainWindow] = None,
    ) -> None:
        super().__init__(parent)
        self.child = child
        self.ui: Union[
            Ui_FrequencyFileGeneratorDialog, Ui_ReadabilityReportGeneratorDialog
        ]

        if self.child == "FrequencyFileGeneratorDialog":
            self.ui = Ui_FrequencyFileGeneratorDialog()
        elif self.child == "ReadabilityReportGeneratorDialog":
            self.ui = Ui_ReadabilityReportGeneratorDialog()

        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self._morphemizers = morphemizer.get_all_morphemizers()
        self._populate_morphemizers()
        self._setup_checkboxes()
        self._input_dir_root: Path

    def _populate_morphemizers(self) -> None:
        morphemizer_names = [mizer.get_description() for mizer in self._morphemizers]
        morphemizers_cbox = self.ui.comboBox
        morphemizers_cbox.addItems(morphemizer_names)

    def _setup_checkboxes(self) -> None:
        self.ui.txtFilesCheckBox.setChecked(True)
        self.ui.srtFilesCheckBox.setChecked(True)
        self.ui.vttFilesCheckBox.setChecked(True)
        self.ui.mdFilesCheckBox.setChecked(True)

    def _on_input_button_clicked(self) -> None:
        input_dir: str = QFileDialog.getExistingDirectory(
            caption="Directory with files to analyze",
            directory=QDir().homePath(),
        )
        self.ui.inputDirLineEdit.setText(input_dir)

    def _gather_input_files(self) -> list[Path]:
        assert mw is not None

        input_files: list[Path] = []
        input_dir = self.ui.inputDirLineEdit.text()
        self._input_dir_root = Path(input_dir)
        extensions = self._get_checked_extensions()

        for extension in extensions:
            if mw.progress.want_cancel():  # user clicked 'x'
                raise CancelledOperationException
            mw.taskman.run_on_main(
                partial(
                    mw.progress.update,
                    label=f"Gathering {extension} files",
                )
            )
            for path in Path(input_dir).rglob(extension):
                if mw.progress.want_cancel():  # user clicked 'x'
                    raise CancelledOperationException
                input_files.append(path)

        return input_files

    def _get_checked_extensions(self) -> list[str]:
        extensions = []

        if self.ui.txtFilesCheckBox.isChecked():
            extensions.append("*.txt")
        if self.ui.srtFilesCheckBox.isChecked():
            extensions.append("*.srt")
        if self.ui.vttFilesCheckBox.isChecked():
            extensions.append("*.vtt")
        if self.ui.mdFilesCheckBox.isChecked():
            extensions.append("*.md")

        return extensions

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

    def _get_morphs_from_line(  # type: ignore[no-untyped-def]
        self, _morphemizer: Morphemizer, nlp, line: str
    ) -> set[Morpheme]:
        # todo: this is horrible, create a callback or something
        if nlp is None:
            return self._get_morphs_from_line_morphemizer(_morphemizer, line)
        return self._get_morphs_from_line_spacy(nlp, line)

    def _get_morphs_from_line_spacy(self, nlp, line: str) -> set[Morpheme]:  # type: ignore[no-untyped-def]
        # nlp: spacy.Language

        morphs: set[Morpheme] = set()
        expression = self._filter_expression(line)

        doc = nlp(expression)

        for w in doc:
            if not w.is_alpha:
                continue

            if self.ui.namesMorphemizerCheckBox.isChecked():
                if w.pos == 96:  # PROPN
                    continue

            morphs.add(
                Morpheme(
                    base=w.lemma_,
                    inflected=w.text,
                )
            )

        if self.ui.namesFileCheckBox.isChecked():
            morphs = remove_names_textfile(morphs)

        return morphs

    def _get_morphs_from_line_morphemizer(
        self, _morphemizer: Morphemizer, line: str
    ) -> set[Morpheme]:
        expression = self._filter_expression(line)
        morphs: set[Morpheme] = _morphemizer.get_morphemes_from_expr(expression)
        if self.ui.namesMorphemizerCheckBox.isChecked():
            morphs = text_preprocessing.remove_names_morphemizer(morphs)
        if self.ui.namesFileCheckBox.isChecked():
            morphs = text_preprocessing.remove_names_textfile(morphs)
        return morphs

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()

        dialog_name: str = ""
        if self.child == "FrequencyFileGeneratorDialog":
            dialog_name = ankimorphs_globals.FREQUENCY_FILE_GENERATOR_DIALOG_NAME
        elif self.child == "ReadabilityReportGeneratorDialog":
            dialog_name = ankimorphs_globals.READABILITY_REPORT_GENERATOR_DIALOG_NAME

        aqt.dialogs.markClosed(dialog_name)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()

    def _on_success(self, result: Any) -> None:
        # This function runs on the main thread.
        del result  # unused
        assert mw is not None
        assert mw.progress is not None

        mw.toolbar.draw()  # updates stats
        mw.progress.finish()

        if self.child == "FrequencyFileGeneratorDialog":
            tooltip("Frequency list generated", parent=self)
        elif self.child == "ReadabilityReportGeneratorDialog":
            tooltip("Readability report generated", parent=self)

    def _on_failure(
        self,
        error: Union[
            Exception,
            CancelledOperationException,
            EmptyFileSelectionException,
            SpacyNotInstalledException,
        ],
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            if self.child == "FrequencyFileGeneratorDialog":
                tooltip("Cancelled Frequency File Generator")
            elif self.child == "ReadabilityReportGeneratorDialog":
                tooltip("Cancelled Readability Report Generator")
        elif isinstance(error, EmptyFileSelectionException):
            tooltip("No file/folder selected")
        elif isinstance(error, SpacyNotInstalledException):
            # todo display error window
            tooltip("SpacyNotInstalledException")
        else:
            raise error
