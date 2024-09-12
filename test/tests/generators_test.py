from __future__ import annotations

from pathlib import Path
from test import test_utils
from test.fake_configs import (
    config_big_japanese_collection,
    config_inflection_evaluation,
    config_lemma_evaluation,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)
from test.test_globals import (
    PATH_TESTS_DATA,
    PATH_TESTS_DATA_CORRECT_OUTPUTS,
    PATH_TESTS_DATA_TESTS_OUTPUTS,
)
from typing import Any

import pytest
from aqt.qt import QTableWidgetItem  # pylint:disable=no-name-in-module

from ankimorphs.generators import (
    priority_file_generator,
    readability_report_generator,
    study_plan_generator,
)
from ankimorphs.generators.generators_output_dialog import (
    GeneratorOutputDialog,
    OutputOptions,
)
from ankimorphs.generators.generators_utils import Column
from ankimorphs.generators.generators_window import GeneratorWindow

################################################################
#            CASE: BIG JAPANESE COLLECTION
################################################################
# Checks the priority files generated with using the am_db from
# the `big_japanese_collection.anki2`.
# The collection is arbitrary since the generators only use the
# found db.
################################################################
case_big_japanese_collection_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
    am_db="big_japanese_collection.db",
)


@pytest.mark.parametrize(
    "fake_environment_fixture, morphemizer_description, only_store_lemma, comprehension_cutoff, expected_output_file",
    [
        (
            case_big_japanese_collection_params,
            "spaCy: ja_core_news_sm",
            True,
            True,
            "ja_core_news_sm_freq_lemma_comprehension.csv",
        ),
        (
            case_big_japanese_collection_params,
            "spaCy: ja_core_news_sm",
            True,
            False,
            "ja_core_news_sm_freq_lemma_min_occurrence.csv",
        ),
        (
            case_big_japanese_collection_params,
            "spaCy: ja_core_news_sm",
            False,
            True,
            "ja_core_news_sm_freq_inflection_comprehension.csv",
        ),
        (
            case_big_japanese_collection_params,
            "spaCy: ja_core_news_sm",
            False,
            False,
            "ja_core_news_sm_freq_inflection_min_occurrence.csv",
        ),
        (
            case_big_japanese_collection_params,
            "AnkiMorphs: Japanese",
            True,
            True,
            "mecab_freq_lemma_comprehension.csv",
        ),
        (
            case_big_japanese_collection_params,
            "AnkiMorphs: Japanese",
            True,
            False,
            "mecab_freq_lemma_min_occurrence.csv",
        ),
        (
            case_big_japanese_collection_params,
            "AnkiMorphs: Japanese",
            False,
            True,
            "mecab_freq_inflection_comprehension.csv",
        ),
        (
            case_big_japanese_collection_params,
            "AnkiMorphs: Japanese",
            False,
            False,
            "mecab_freq_inflection_min_occurrence.csv",
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_priority_file_generator(  # pylint:disable=unused-argument, too-many-arguments
    fake_environment_fixture: FakeEnvironment,
    morphemizer_description: str,
    only_store_lemma: bool,
    comprehension_cutoff: bool,
    expected_output_file: str,
    qtbot: Any,
) -> None:
    """
    All of these files has the additional "occurrences" column, i.e. the
    option "add occurrences column" is always used.
    """
    gw = GeneratorWindow()

    input_folder = Path(PATH_TESTS_DATA, "ja_subs")
    test_output_file = Path(PATH_TESTS_DATA_TESTS_OUTPUTS, "test_output_file.csv")

    expected_output_file_path = Path(
        PATH_TESTS_DATA_CORRECT_OUTPUTS,
        expected_output_file,
    )

    print(f"loaded file: {expected_output_file_path}")

    gw.ui.inputDirLineEdit.setText(str(input_folder))
    gw._background_gather_files_and_populate_files_column()

    _set_morphemizer(
        generator_window=gw, morphemizer_description=morphemizer_description
    )

    selected_output = GeneratorOutputDialog(priority_file_mode=True)
    selected_output.ui.outputLineEdit.setText(str(test_output_file))
    selected_output.ui.addOccurrencesColumnCheckBox.setChecked(True)

    if only_store_lemma:
        selected_output.ui.storeOnlyMorphLemmaRadioButton.setChecked(True)
        selected_output.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(False)
    if comprehension_cutoff:
        selected_output.ui.comprehensionRadioButton.setChecked(True)
        selected_output.ui.minOccurrenceRadioButton.setChecked(False)

    selected_output_options: OutputOptions = selected_output.get_selected_options()

    priority_file_generator.background_generate_priority_file(
        selected_output_options=selected_output_options,
        ui=gw.ui,
        morphemizers=gw._morphemizers,
        input_dir_root=gw._input_dir_root,
        input_files=gw._input_files,
    )

    test_utils.assert_csv_files_are_identical(
        correct_output_file=expected_output_file_path, test_output_file=test_output_file
    )


def _set_morphemizer(
    generator_window: GeneratorWindow, morphemizer_description: str
) -> None:
    index = -1
    for _index, mizer in enumerate(generator_window._morphemizers):
        # print(f"mizer.get_description(): {mizer.get_description()}")
        if mizer.get_description() == morphemizer_description:
            index = _index
    # print(f"index: {index}")
    generator_window.ui.morphemizerComboBox.setCurrentIndex(index)


################################################################
#            CASES: SOME STUDIED JAPANESE
################################################################
# Checks if that the readability reports gives the correct
# values in the readability report with the specified
# db and the respective morphs evaluation options
################################################################
case_some_studied_japanese_inflections = FakeEnvironmentParams(
    actual_col="some_studied_japanese_collection",
    expected_col="some_studied_japanese_collection",
    config=config_inflection_evaluation,
    am_db="some_studied_japanese.db",
)

case_some_studied_japanese_lemmas = FakeEnvironmentParams(
    actual_col="some_studied_japanese_collection",
    expected_col="some_studied_japanese_collection",
    config=config_lemma_evaluation,
    am_db="some_studied_japanese.db",
)


@pytest.mark.parametrize(
    "fake_environment_fixture, unique_known_number, unique_known_percent, total_known_number, total_known_percent",
    [
        (case_some_studied_japanese_inflections, "4", "0.8 %", "52", "3.1 %"),
        (case_some_studied_japanese_lemmas, "17", "3.5 %", "91", "5.5 %"),
    ],
    indirect=["fake_environment_fixture"],
)
def test_readability_report(  # pylint:disable=too-many-arguments, unused-argument
    fake_environment_fixture: FakeEnvironment,
    unique_known_number: str,
    unique_known_percent: str,
    total_known_number: str,
    total_known_percent: str,
    qtbot: Any,
) -> None:
    gw = GeneratorWindow()
    input_folder = Path(PATH_TESTS_DATA, "ja_subs")
    gw.ui.inputDirLineEdit.setText(str(input_folder))

    gw._background_gather_files_and_populate_files_column()

    _set_morphemizer(
        generator_window=gw, morphemizer_description="AnkiMorphs: Japanese"
    )

    readability_report_generator.background_generate_report(
        ui=gw.ui,
        morphemizers=gw._morphemizers,
        input_dir_root=gw._input_dir_root,
        input_files=gw._input_files,
    )

    _row = 1
    _item: QTableWidgetItem | None

    _item = gw.ui.numericalTableWidget.item(_row, Column.FILE_NAME.value)
    assert _item is not None
    assert _item.text() == "Black Clover - 002 - The Boys` Promise [shiRo].jp.srt"

    _item = gw.ui.percentTableWidget.item(_row, Column.FILE_NAME.value)
    assert _item is not None
    assert _item.text() == "Black Clover - 002 - The Boys` Promise [shiRo].jp.srt"

    _item = gw.ui.numericalTableWidget.item(_row, Column.UNIQUE_MORPHS.value)
    assert _item is not None
    assert _item.text() == "482"

    _item = gw.ui.percentTableWidget.item(_row, Column.UNIQUE_MORPHS.value)
    assert _item is not None
    assert _item.text() == "482"

    _item = gw.ui.numericalTableWidget.item(_row, Column.UNIQUE_KNOWN.value)
    assert _item is not None
    assert _item.text() == unique_known_number

    _item = gw.ui.percentTableWidget.item(_row, Column.UNIQUE_KNOWN.value)
    assert _item is not None
    assert _item.text() == unique_known_percent

    _item = gw.ui.numericalTableWidget.item(_row, Column.TOTAL_MORPHS.value)
    assert _item is not None
    assert _item.text() == "1656"

    _item = gw.ui.percentTableWidget.item(_row, Column.TOTAL_MORPHS.value)
    assert _item is not None
    assert _item.text() == "1656"

    _item = gw.ui.numericalTableWidget.item(_row, Column.TOTAL_KNOWN.value)
    assert _item is not None
    assert _item.text() == total_known_number

    _item = gw.ui.percentTableWidget.item(_row, Column.TOTAL_KNOWN.value)
    assert _item is not None
    assert _item.text() == total_known_percent


@pytest.mark.parametrize(
    "fake_environment_fixture, only_store_lemma, expected_output_file",
    [
        (case_some_studied_japanese_inflections, True, "mecab_study_plan_lemma.csv"),
        (
            case_some_studied_japanese_inflections,
            False,
            "mecab_study_plan_inflection.csv",
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_study_plan_generator(  # pylint:disable=unused-argument, too-many-locals
    fake_environment_fixture: FakeEnvironment,
    only_store_lemma: bool,
    expected_output_file: str,
    qtbot: Any,
) -> None:
    gw = GeneratorWindow()

    input_folder = Path(PATH_TESTS_DATA, "ja_subs")
    test_output_file = Path(
        PATH_TESTS_DATA_TESTS_OUTPUTS, "mecab_study_plan_test_output.csv"
    )

    expected_output_file_path = Path(
        PATH_TESTS_DATA_CORRECT_OUTPUTS,
        expected_output_file,
    )

    gw.ui.inputDirLineEdit.setText(str(input_folder))
    gw._background_gather_files_and_populate_files_column()

    _set_morphemizer(
        generator_window=gw, morphemizer_description="AnkiMorphs: Japanese"
    )

    _default_output_file = Path(test_output_file)
    selected_output = GeneratorOutputDialog(study_plan_mode=True)
    selected_output.ui.outputLineEdit.setText(str(test_output_file))
    selected_output_options: OutputOptions = selected_output.get_selected_options()
    selected_output_options.selected_extra_occurrences_column = True

    # additional test of using minimum occurrence: 2
    selected_output_options.min_occurrence = True
    selected_output_options.min_occurrence_threshold = 2

    if only_store_lemma:
        selected_output_options.store_only_lemma = True
        selected_output_options.store_lemma_and_inflection = False
    else:
        selected_output_options.store_only_lemma = False
        selected_output_options.store_lemma_and_inflection = True

    study_plan_generator.background_generate_study_plan(
        selected_output_options=selected_output_options,
        ui=gw.ui,
        morphemizers=gw._morphemizers,
        input_dir_root=gw._input_dir_root,
        input_files=gw._input_files,
    )

    test_utils.assert_csv_files_are_identical(
        correct_output_file=expected_output_file_path, test_output_file=test_output_file
    )
