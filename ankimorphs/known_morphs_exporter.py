from __future__ import annotations

import csv
import datetime
import os
from pathlib import Path
from typing import Any, Callable

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QDialog, QDir, QFileDialog  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from . import ankimorphs_globals as am_globals
from .ankimorphs_config import AnkiMorphsConfig
from .ankimorphs_db import AnkiMorphsDB
from .exceptions import CancelledOperationException, EmptyFileSelectionException
from .ui.known_morphs_exporter_dialog_ui import Ui_KnownMorphsExporterDialog


class KnownMorphsExporterDialog(QDialog):
    def __init__(
        self,
    ) -> None:
        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.ui = Ui_KnownMorphsExporterDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self.ui.knownIntervalSpinBox.setValue(21)  # usually considered known

        self._setup_output_path()
        self._setup_buttons()

        self.show()

    def _setup_output_path(self) -> None:
        assert mw is not None

        _output_dir = os.path.join(
            mw.pm.profileFolder(), am_globals.KNOWN_MORPHS_DIR_NAME
        )
        # create the parent directories if they don't exist
        Path(_output_dir).parent.mkdir(parents=True, exist_ok=True)
        self.ui.outputLineEdit.setText(_output_dir)

    def _setup_buttons(self) -> None:
        self.ui.selectOutputPushButton.setAutoDefault(False)
        self.ui.exportKnownMorphsPushButton.setAutoDefault(False)

        self.ui.selectOutputPushButton.clicked.connect(self._on_output_button_clicked)
        self.ui.exportKnownMorphsPushButton.clicked.connect(self._export_known_morphs)

        am_config = AnkiMorphsConfig()
        if am_config.evaluate_morph_lemma:
            self.ui.storeOnlyMorphLemmaRadioButton.setChecked(True)
            self.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(False)
        else:
            self.ui.storeOnlyMorphLemmaRadioButton.setChecked(False)
            self.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(True)

    def _on_output_button_clicked(self) -> None:
        output_dir: str = QFileDialog.getExistingDirectory(
            caption="Directory to place file",
            directory=QDir().homePath(),
        )
        self.ui.outputLineEdit.setText(output_dir)

    def _export_known_morphs(self) -> None:
        assert mw is not None

        mw.progress.start(label="Exporting Known Morphs")
        operation = QueryOp(
            parent=mw,
            op=lambda _: self._background_export_known_morphs(),
            success=self._on_success,
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _background_export_known_morphs(  # pylint:disable=too-many-locals
        self,
    ) -> None:
        assert mw is not None

        if self.ui.outputLineEdit.text() == "":
            raise EmptyFileSelectionException

        output_dir = self.ui.outputLineEdit.text()
        _datetime = datetime.datetime.now().strftime("%Y-%m-%d@%H-%M-%S")
        output_file = os.path.join(output_dir, f"known_morphs-{_datetime}.csv")

        # create the parent directories if they don't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        selected_extra_occurrences_column: bool = (
            self.ui.addOccurrencesColumnCheckBox.isChecked()
        )
        known_interval: int = self.ui.knownIntervalSpinBox.value()
        store_only_lemma: bool = self.ui.storeOnlyMorphLemmaRadioButton.isChecked()

        if store_only_lemma:
            self._export_lemmas(
                output_file=output_file,
                known_interval=known_interval,
                selected_extra_occurrences_column=selected_extra_occurrences_column,
            )
        else:
            self._export_inflections(
                output_file=output_file,
                known_interval=known_interval,
                selected_extra_occurrences_column=selected_extra_occurrences_column,
            )

    @staticmethod
    def _export_inflections(
        output_file: str,
        known_interval: int,
        selected_extra_occurrences_column: bool,
    ) -> None:
        headers: list[str] = [am_globals.LEMMA_HEADER, am_globals.INFLECTION_HEADER]
        if selected_extra_occurrences_column:
            headers.append("Occurrence")

        export_list: list[tuple[str, str, int]] = (
            AnkiMorphsDB().get_lemmas_and_inflections_with_count(known_interval)
        )

        with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
            morph_writer = csv.writer(csvfile)
            morph_writer.writerow(headers)

            if selected_extra_occurrences_column:
                for lemma, inflection, inflection_count in export_list:
                    morph_writer.writerow([lemma, inflection, inflection_count])
            else:
                for lemma, inflection, _ in export_list:
                    morph_writer.writerow([lemma, inflection])

    @staticmethod
    def _export_lemmas(
        output_file: str,
        known_interval: int,
        selected_extra_occurrences_column: bool,
    ) -> None:
        headers: list[str] = [am_globals.LEMMA_HEADER]
        if selected_extra_occurrences_column is True:
            headers.append("Occurrence")

        export_list: list[tuple[str, int]] = AnkiMorphsDB().get_known_lemmas_with_count(
            known_interval
        )

        with open(output_file, mode="w+", encoding="utf-8", newline="") as csvfile:
            morph_writer = csv.writer(csvfile)
            morph_writer.writerow(headers)

            if selected_extra_occurrences_column:
                for lemma, count in export_list:
                    morph_writer.writerow([lemma, count])
            else:
                for lemma, _ in export_list:
                    morph_writer.writerow([lemma])

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        # This is used by the Anki dialog manager
        self.close()
        aqt.dialogs.markClosed(am_globals.KNOWN_MORPHS_EXPORTER_DIALOG_NAME)
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

        tooltip("Known morphs file created", parent=self)

    def _on_failure(
        self,
        error: Exception | CancelledOperationException | EmptyFileSelectionException,
    ) -> None:
        # This function runs on the main thread.
        assert mw is not None
        assert mw.progress is not None
        mw.progress.finish()

        if isinstance(error, CancelledOperationException):
            tooltip("Cancelled Known Morphs Export", parent=self)
        elif isinstance(error, EmptyFileSelectionException):
            tooltip("No file/folder selected", parent=self)
        else:
            raise error
