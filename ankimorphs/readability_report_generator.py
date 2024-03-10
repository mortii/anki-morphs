from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import TextIO

from anki.collection import Collection
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAbstractItemView,
    QHeaderView,
    Qt,
    QTableWidget,
    QTableWidgetItem,
)

from . import spacy_wrapper
from .ankimorphs_config import AnkiMorphsConfig
from .ankimorphs_db import AnkiMorphsDB
from .exceptions import CancelledOperationException, EmptyFileSelectionException
from .generator_dialog import GeneratorDialog
from .morpheme import Morpheme, MorphOccurrence
from .morphemizer import Morphemizer, SpacyMorphemizer
from .table_utils import QTableWidgetIntegerItem, QTableWidgetPercentItem
from .ui.readability_report_generator_ui import Ui_ReadabilityReportGeneratorWindow


class FileMorphsStats:
    __slots__ = (
        "unique_morphs",
        "unique_known",
        "unique_learning",
        "unique_unknowns",
        "total_morphs",
        "total_known",
        "total_learning",
        "total_unknowns",
    )

    def __init__(
        self,
    ) -> None:
        self.unique_known: set[Morpheme] = set()
        self.unique_learning: set[Morpheme] = set()
        self.unique_unknowns: set[Morpheme] = set()

        self.total_known = 0
        self.total_learning = 0
        self.total_unknowns = 0

    def __add__(self, other: FileMorphsStats) -> FileMorphsStats:
        self.unique_known.update(other.unique_known)
        self.unique_learning.update(other.unique_learning)
        self.unique_unknowns.update(other.unique_unknowns)

        self.total_known += other.total_known
        self.total_learning += other.total_learning
        self.total_unknowns += other.total_unknowns

        return self


class ReadabilityReportGeneratorDialog(  # pylint:disable=too-many-instance-attributes
    GeneratorDialog
):
    # ReadabilityReportGeneratorDialog inherits from GeneratorDialog, so if you cannot find
    # a self.[...] function or property, look there.

    def __init__(self) -> None:
        super().__init__(child=self.__class__.__name__)
        assert isinstance(self.ui, Ui_ReadabilityReportGeneratorWindow)

        self.file_name_column = 0

        self._unique_morphs_column = 1
        self._unique_known_column = 2
        self._unique_learning_column = 3
        self._unique_unknowns_column = 4

        self._total_morphs_column = 5
        self._total_known_column = 6
        self._total_learning_column = 7
        self._total_unknowns_column = 8

        self._number_of_columns = 9

        self._setup_table(self.ui.numericalTableWidget)
        self._setup_table(self.ui.percentTableWidget)
        self._setup_buttons()
        self.show()

    def _setup_table(self, table: QTableWidget) -> None:
        assert isinstance(self.ui, Ui_ReadabilityReportGeneratorWindow)

        table.setAlternatingRowColors(True)
        table.setColumnCount(self._number_of_columns)

        table.setColumnWidth(self.file_name_column, 200)
        table.setColumnWidth(self._unique_morphs_column, 90)
        table.setColumnWidth(self._unique_known_column, 90)
        table.setColumnWidth(self._unique_learning_column, 90)
        table.setColumnWidth(self._unique_unknowns_column, 90)
        table.setColumnWidth(self._total_morphs_column, 90)
        table.setColumnWidth(self._total_known_column, 90)
        table.setColumnWidth(self._total_learning_column, 90)
        table.setColumnWidth(self._total_unknowns_column, 90)

        table_horizontal_headers: QHeaderView | None = table.horizontalHeader()
        assert table_horizontal_headers is not None
        table_horizontal_headers.setSectionsMovable(True)

        # disables manual editing of the table
        self.ui.numericalTableWidget.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

    def _setup_buttons(self) -> None:
        assert isinstance(self.ui, Ui_ReadabilityReportGeneratorWindow)
        self.ui.inputPushButton.clicked.connect(self._on_input_button_clicked)
        self.ui.generateReportPushButton.clicked.connect(self._generate_report)

    def _generate_report(self) -> None:
        assert mw is not None
        mw.progress.start(label="Generating readability report")
        operation = QueryOp(
            parent=mw,
            op=self._background_generate_report,
            success=self._on_success,
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _background_generate_report(  # pylint:disable=too-many-locals
        self, col: Collection
    ) -> None:
        del col  # unused
        assert mw is not None
        assert isinstance(self.ui, Ui_ReadabilityReportGeneratorWindow)

        if self.ui.inputDirLineEdit.text() == "":
            raise EmptyFileSelectionException

        input_files: list[Path] = self._gather_input_files()
        # without this sorting, the initial report will have a (seemingly) random order
        input_files.sort(key=lambda _file: _file.name)

        nlp = None  # spacy.Language
        morphemizer: Morphemizer = self._morphemizers[self.ui.comboBox.currentIndex()]
        assert morphemizer is not None

        if isinstance(morphemizer, SpacyMorphemizer):
            selected: str = self.ui.comboBox.itemText(self.ui.comboBox.currentIndex())
            spacy_model = selected.removeprefix("spaCy: ")
            nlp = spacy_wrapper.get_nlp(spacy_model)

        # sorting has to be disabled before populating because bugs can occur
        self.ui.numericalTableWidget.setSortingEnabled(False)
        self.ui.percentTableWidget.setSortingEnabled(False)

        # clear previous results
        self.ui.numericalTableWidget.clearContents()
        self.ui.percentTableWidget.clearContents()

        files_morph_dicts: dict[Path, dict[str, MorphOccurrence]] = {}

        for input_file in input_files:
            if mw.progress.want_cancel():  # user clicked 'x' button
                raise CancelledOperationException

            mw.taskman.run_on_main(
                partial(
                    mw.progress.update,
                    label=f"Reading file:<br>{input_file.relative_to(self._input_dir_root)}",
                )
            )

            with open(input_file, encoding="utf-8") as file:
                file_morphs: dict[str, MorphOccurrence] = self._create_file_morphs_dict(
                    file, morphemizer, nlp
                )
                files_morph_dicts[input_file] = file_morphs

        mw.taskman.run_on_main(
            partial(
                mw.progress.update,
                label="Generating Report...",
            )
        )

        am_config = AnkiMorphsConfig()
        am_db = AnkiMorphsDB()

        self.ui.numericalTableWidget.setRowCount(len(input_files) + 1)
        self.ui.percentTableWidget.setRowCount(len(input_files) + 1)

        # the global report will be presented as a "Total" file in the table
        global_report_morph_stats = FileMorphsStats()

        for _row, _input_file in enumerate(input_files):
            file_morphs = files_morph_dicts[_input_file]

            file_morphs_stats = self._get_morph_stats_from_file(
                am_config, am_db, file_morphs
            )
            global_report_morph_stats += file_morphs_stats

            self._populate_numerical_table(_input_file, _row, file_morphs_stats)
            self._populate_percentage_table(_input_file, _row, file_morphs_stats)

        fake_input_file = Path(self._input_dir_root, "Total")

        self._populate_numerical_table(
            _input_file=fake_input_file,
            _row=len(input_files),
            file_morphs_stats=global_report_morph_stats,
        )
        self._populate_percentage_table(
            _input_file=fake_input_file,
            _row=len(input_files),
            file_morphs_stats=global_report_morph_stats,
        )

        self.ui.numericalTableWidget.setSortingEnabled(True)
        self.ui.percentTableWidget.setSortingEnabled(True)

        am_db.con.close()

    def _create_file_morphs_dict(self, file: TextIO, morphemizer, nlp) -> dict[str, MorphOccurrence]:  # type: ignore[no-untyped-def]
        # nlp: spacy.Language

        file_morphs: dict[str, MorphOccurrence] = {}
        for line in file:
            morphs: list[Morpheme] = self._get_morphs_from_line(morphemizer, nlp, line)
            for morph in morphs:
                key = morph.lemma + morph.inflection
                if key in file_morphs:
                    file_morphs[key].occurrence += 1
                else:
                    file_morphs[key] = MorphOccurrence(morph)
        return file_morphs

    @staticmethod
    def _get_morph_stats_from_file(
        am_config: AnkiMorphsConfig,
        am_db: AnkiMorphsDB,
        file_morphs: dict[str, MorphOccurrence],
    ) -> FileMorphsStats:
        file_morphs_stats = FileMorphsStats()

        for morph_occurrence_object in file_morphs.values():
            morph = morph_occurrence_object.morph
            occurrence = morph_occurrence_object.occurrence

            highest_learning_interval: int | None = am_db.get_highest_learning_interval(
                morph.lemma, morph.inflection
            )

            if highest_learning_interval is None:
                file_morphs_stats.total_unknowns += occurrence
                file_morphs_stats.unique_unknowns.add(morph)
                continue

            if highest_learning_interval == 0:
                file_morphs_stats.total_unknowns += occurrence
                file_morphs_stats.unique_unknowns.add(morph)
            elif highest_learning_interval < am_config.recalc_interval_for_known:
                file_morphs_stats.total_learning += occurrence
                file_morphs_stats.unique_learning.add(morph)
            else:
                file_morphs_stats.total_known += occurrence
                file_morphs_stats.unique_known.add(morph)

        return file_morphs_stats

    def _populate_numerical_table(
        self,
        _input_file: Path,
        _row: int,
        file_morphs_stats: FileMorphsStats,
    ) -> None:
        assert isinstance(self.ui, Ui_ReadabilityReportGeneratorWindow)

        file_name = str(_input_file.relative_to(self._input_dir_root))

        unique_morphs: int = (
            len(file_morphs_stats.unique_known)
            + len(file_morphs_stats.unique_learning)
            + len(file_morphs_stats.unique_unknowns)
        )

        total_morphs: int = (
            file_morphs_stats.total_known
            + file_morphs_stats.total_learning
            + file_morphs_stats.total_unknowns
        )

        file_name_item = QTableWidgetItem(file_name)

        unique_morphs_item = QTableWidgetIntegerItem(unique_morphs)
        unique_known_item = QTableWidgetIntegerItem(len(file_morphs_stats.unique_known))
        unique_learning_item = QTableWidgetIntegerItem(
            len(file_morphs_stats.unique_learning)
        )
        unique_unknowns_item = QTableWidgetIntegerItem(
            len(file_morphs_stats.unique_unknowns)
        )

        total_morphs_item = QTableWidgetIntegerItem(total_morphs)
        total_known_item = QTableWidgetIntegerItem(file_morphs_stats.total_known)
        total_learning_item = QTableWidgetIntegerItem(file_morphs_stats.total_learning)
        total_unknown_item = QTableWidgetIntegerItem(file_morphs_stats.total_unknowns)

        unique_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unique_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unique_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unique_unknowns_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        total_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_unknown_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ui.numericalTableWidget.setItem(
            _row, self.file_name_column, file_name_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._unique_morphs_column, unique_morphs_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._unique_known_column, unique_known_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._unique_learning_column, unique_learning_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._unique_unknowns_column, unique_unknowns_item
        )

        self.ui.numericalTableWidget.setItem(
            _row, self._total_morphs_column, total_morphs_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._total_known_column, total_known_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._total_learning_column, total_learning_item
        )
        self.ui.numericalTableWidget.setItem(
            _row, self._total_unknowns_column, total_unknown_item
        )

    def _populate_percentage_table(  # pylint:disable=too-many-locals
        self,
        _input_file: Path,
        _row: int,
        file_morphs_stats: FileMorphsStats,
    ) -> None:
        assert isinstance(self.ui, Ui_ReadabilityReportGeneratorWindow)

        file_name = str(_input_file.relative_to(self._input_dir_root))

        unique_morphs: int = (
            len(file_morphs_stats.unique_known)
            + len(file_morphs_stats.unique_learning)
            + len(file_morphs_stats.unique_unknowns)
        )

        total_morphs: int = (
            file_morphs_stats.total_known
            + file_morphs_stats.total_learning
            + file_morphs_stats.total_unknowns
        )

        unique_known_percent: float = 0
        unique_learning_percent: float = 0
        unique_unknown_percent: float = 0

        total_known_percent: float = 0
        total_learning_percent: float = 0
        total_unknown_percent: float = 0

        if unique_morphs != 0:
            unique_known_percent = (
                len(file_morphs_stats.unique_known) / unique_morphs
            ) * 100

            unique_learning_percent = (
                len(file_morphs_stats.unique_learning) / unique_morphs
            ) * 100

            unique_unknown_percent = (
                len(file_morphs_stats.unique_unknowns) / unique_morphs
            ) * 100

        if total_morphs != 0:
            total_known_percent = (file_morphs_stats.total_known / total_morphs) * 100

            total_learning_percent = (
                file_morphs_stats.total_learning / total_morphs
            ) * 100

            total_unknown_percent = (
                file_morphs_stats.total_unknowns / total_morphs
            ) * 100

        file_name_item = QTableWidgetItem(file_name)

        unique_morphs_item = QTableWidgetIntegerItem(unique_morphs)
        unique_known_item = QTableWidgetPercentItem(round(unique_known_percent, 1))
        unique_learning_item = QTableWidgetPercentItem(
            round(unique_learning_percent, 1)
        )
        unique_unknowns_item = QTableWidgetPercentItem(round(unique_unknown_percent, 1))

        total_morphs_item = QTableWidgetIntegerItem(total_morphs)
        total_known_item = QTableWidgetPercentItem(round(total_known_percent, 1))
        total_learning_item = QTableWidgetPercentItem(round(total_learning_percent, 1))
        total_unknown_item = QTableWidgetPercentItem(round(total_unknown_percent, 1))

        unique_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unique_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unique_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        unique_unknowns_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_morphs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_known_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_learning_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_unknown_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ui.percentTableWidget.setItem(_row, self.file_name_column, file_name_item)
        self.ui.percentTableWidget.setItem(
            _row, self._unique_morphs_column, unique_morphs_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._unique_known_column, unique_known_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._unique_learning_column, unique_learning_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._unique_unknowns_column, unique_unknowns_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._total_morphs_column, total_morphs_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._total_known_column, total_known_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._total_learning_column, total_learning_item
        )
        self.ui.percentTableWidget.setItem(
            _row, self._total_unknowns_column, total_unknown_item
        )
