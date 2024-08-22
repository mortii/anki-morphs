from __future__ import annotations

import csv
import datetime
import os
from pathlib import Path
from typing import Callable

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QDialog, QFileDialog  # pylint:disable=no-name-in-module
from aqt.utils import tooltip

from . import ankimorphs_globals as am_globals
from .ankimorphs_config import AnkiMorphsConfig
from .ankimorphs_db import AnkiMorphsDB
from .exceptions import CancelledOperationException, EmptyFileSelectionException
from .extra_settings import extra_settings_keys
from .extra_settings.ankimorphs_extra_settings import AnkiMorphsExtraSettings
from .ui.known_morphs_exporter_dialog_ui import Ui_KnownMorphsExporterDialog


class KnownMorphsExporterDialog(QDialog):
    def __init__(
        self,
    ) -> None:
        assert mw is not None

        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.ui = Ui_KnownMorphsExporterDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.am_config = AnkiMorphsConfig()

        self.am_extra_settings = AnkiMorphsExtraSettings()
        self.am_extra_settings.beginGroup(
            extra_settings_keys.Dialogs.KNOWN_MORPHS_EXPORTER
        )

        self._default_output_dir = os.path.join(
            mw.pm.profileFolder(), am_globals.KNOWN_MORPHS_DIR_NAME
        )

        self._setup_output_path()
        self._setup_buttons()
        self._setup_spinbox()
        self._setup_checkboxes()
        self._setup_geometry()

        self.am_extra_settings.endGroup()
        self.show()

    def _setup_output_path(self) -> None:
        stored_output_dir: str = self.am_extra_settings.value(
            extra_settings_keys.KnownMorphsExporterKeys.OUTPUT_DIR,
            defaultValue=self._default_output_dir,
            type=str,
        )

        # create the parent directories if they don't exist
        Path(stored_output_dir).parent.mkdir(parents=True, exist_ok=True)
        self.ui.outputLineEdit.setText(stored_output_dir)

    def _setup_buttons(self) -> None:
        self.ui.selectOutputPushButton.setAutoDefault(False)
        self.ui.exportKnownMorphsPushButton.setAutoDefault(False)

        self.ui.selectOutputPushButton.clicked.connect(self._on_output_button_clicked)
        self.ui.exportKnownMorphsPushButton.clicked.connect(self._export_known_morphs)

        stored_lemma_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.KnownMorphsExporterKeys.LEMMA,
            defaultValue=self.am_config.evaluate_morph_lemma,
            type=bool,
        )
        stored_inflection_selected: bool = self.am_extra_settings.value(
            extra_settings_keys.KnownMorphsExporterKeys.INFLECTION,
            defaultValue=not self.am_config.evaluate_morph_lemma,
            type=bool,
        )

        self.ui.storeOnlyMorphLemmaRadioButton.setChecked(stored_lemma_selected)
        self.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(
            stored_inflection_selected
        )

    def _setup_spinbox(self) -> None:
        stored_interval: int = self.am_extra_settings.value(
            extra_settings_keys.KnownMorphsExporterKeys.INTERVAL,
            defaultValue=self.am_config.interval_for_known_morphs,
            type=int,
        )
        self.ui.knownIntervalSpinBox.setValue(stored_interval)

    def _setup_checkboxes(self) -> None:
        stored_occurrences_selection: bool = self.am_extra_settings.value(
            extra_settings_keys.KnownMorphsExporterKeys.OCCURRENCES,
            defaultValue=False,
            type=bool,
        )
        self.ui.addOccurrencesColumnCheckBox.setChecked(stored_occurrences_selection)

    def _setup_geometry(self) -> None:
        stored_geometry = self.am_extra_settings.value(
            extra_settings_keys.KnownMorphsExporterKeys.WINDOW_GEOMETRY
        )
        if stored_geometry is not None:
            self.restoreGeometry(stored_geometry)

    def _on_output_button_clicked(self) -> None:
        output_dir: str = QFileDialog.getExistingDirectory(
            directory=self.ui.outputLineEdit.text(),
        )
        if output_dir == "":
            output_dir = self._default_output_dir

        self.ui.outputLineEdit.setText(output_dir)

    def _export_known_morphs(self) -> None:
        assert mw is not None

        mw.progress.start(label="Exporting Known Morphs")
        operation = QueryOp(
            parent=mw,
            op=lambda _: self._background_export_known_morphs(),
            success=lambda _: self._on_success(),
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
            AnkiMorphsDB().get_known_lemmas_and_inflections_with_count(known_interval)
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
        self.am_extra_settings.save_known_morphs_exporter_settings(
            ui=self.ui, geometry=self.saveGeometry()
        )
        self.close()
        aqt.dialogs.markClosed(am_globals.KNOWN_MORPHS_EXPORTER_DIALOG_NAME)
        callback()

    def reopen(self) -> None:
        # This is used by the Anki dialog manager
        self.show()

    def _on_success(self) -> None:
        # This function runs on the main thread.
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
