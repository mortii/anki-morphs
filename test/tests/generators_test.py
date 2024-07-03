from __future__ import annotations

import os
import pprint
from pathlib import Path
from test.fake_configs import (
    config_big_japanese_collection,
    config_inflection_evaluation,
    config_lemma_evaluation,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment,
)
from test.test_globals import (
    PATH_TESTS_DATA,
    PATH_TESTS_DATA_CORRECT_OUTPUTS,
    PATH_TESTS_DATA_TESTS_OUTPUTS,
)
from typing import Any

import pytest
from aqt.qt import QTableWidgetItem  # pylint:disable=no-name-in-module
from csv_diff import compare, load_csv

from ankimorphs.generators.generators_output_dialog import (
    GeneratorOutputDialog,
    OutputOptions,
)
from ankimorphs.generators.generators_window import GeneratorWindow

################################################################
#            CASE: BIG JAPANESE COLLECTION
################################################################
# Checks the frequency files generated with using the am_db from
# the `big_japanese_collection.anki2`.
# The collection is arbitrary since the generators only use the
# found db.
################################################################
case_big_japanese_collection_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
    config=config_big_japanese_collection,
    am_db="big_japanese_collection.db",
)


# when stacking 'parametrize' we run the function with all permutations
@pytest.mark.parametrize(
    "fake_environment",
    [case_big_japanese_collection_params],
    indirect=True,
)
@pytest.mark.parametrize(
    "morphemizer_description",
    ["spaCy: ja_core_news_sm", "AnkiMorphs: Japanese"],
)
@pytest.mark.parametrize(
    "only_lemma",
    [True, False],
)
@pytest.mark.parametrize(
    "comprehension_cutoff",
    [True, False],
)
def test_frequency_file_generator(  # pylint:disable=unused-argument, too-many-locals, too-many-branches
    fake_environment: FakeEnvironment,
    morphemizer_description: str,
    only_lemma: bool,
    comprehension_cutoff: bool,
    qtbot: Any,
) -> None:
    """
    All of these files has the additional "occurrences" column, i.e. the
    option "add occurrences column" is always used.
    """
    gw = GeneratorWindow()

    input_folder = Path(PATH_TESTS_DATA, "ja_subs")
    test_output_file = Path(PATH_TESTS_DATA_TESTS_OUTPUTS, "test_output_file.csv")

    if morphemizer_description == "AnkiMorphs: Japanese":
        if only_lemma:
            if comprehension_cutoff:
                _file_name = "mecab_freq_lemma_comprehension.csv"
            else:
                _file_name = "mecab_freq_lemma_min_occurrence.csv"
        else:
            if comprehension_cutoff:
                _file_name = "mecab_freq_inflection_comprehension.csv"
            else:
                _file_name = "mecab_freq_inflection_min_occurrence.csv"
    else:
        if only_lemma:
            if comprehension_cutoff:
                _file_name = "ja_core_news_sm_freq_lemma_comprehension.csv"
            else:
                _file_name = "ja_core_news_sm_freq_lemma_min_occurrence.csv"
        else:
            if comprehension_cutoff:
                _file_name = "ja_core_news_sm_freq_inflection_comprehension.csv"
            else:
                _file_name = "ja_core_news_sm_freq_inflection_min_occurrence.csv"

    correct_output_file = Path(
        PATH_TESTS_DATA_CORRECT_OUTPUTS,
        _file_name,
    )

    print(f"loaded file: {correct_output_file}")

    gw.ui.inputDirLineEdit.setText(str(input_folder))
    gw._background_gather_files_and_populate_files_column()

    _set_morphemizer(
        generator_window=gw, morphemizer_description=morphemizer_description
    )

    _default_output_file = test_output_file
    selected_output = GeneratorOutputDialog(_default_output_file)
    selected_output.ui.addOccurrencesColumnCheckBox.setChecked(True)

    if only_lemma:
        selected_output.ui.storeOnlyMorphLemmaRadioButton.setChecked(True)
        selected_output.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(False)
    if comprehension_cutoff:
        selected_output.ui.comprehensionRadioButton.setChecked(True)
        selected_output.ui.minOccurrenceRadioButton.setChecked(False)

    selected_output_options: OutputOptions = selected_output.get_selected_options()

    gw._background_generate_frequency_file(selected_output_options)

    with open(correct_output_file, encoding="utf8") as a, open(
        test_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list[Any]] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)
        assert len(diff) != 0
        for changes in diff.values():
            assert len(changes) == 0

    os.remove(test_output_file)


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


# @pytest.mark.parametrize(
#     "fake_environment",
#     [("big-japanese-collection", config_big_japanese_collection)],
#     indirect=True,
# )
# def test_study_plan_generator(  # pylint:disable=unused-argument, too-many-locals
#     fake_environment, qtbot
# ):
#     gd = GeneratorWindow()
#
#     input_folder = Path(TESTS_DATA_PATH, "ja_subs")
#     test_output_file = Path(
#         TESTS_DATA_TESTS_OUTPUTS_PATH, "mecab_study_plan_test_output.csv"
#     )
#     correct_output_file = Path(TESTS_DATA_CORRECT_OUTPUTS_PATH, "mecab_study_plan.csv")
#
#     gd.ui.inputDirLineEdit.setText(str(input_folder))
#     gd._background_gather_files_and_populate_files_column(col=None)
#
#     index = -1
#     for _index, mizer in enumerate(gd._morphemizers):
#         # print(f"mizer.get_description(): {mizer.get_description()}")
#         if mizer.get_description() == "AnkiMorphs: Japanese":
#             index = _index
#
#     # print(f"index: {index}")
#     gd.ui.morphemizerComboBox.setCurrentIndex(index)
#
#     _default_output_file = Path(test_output_file)
#     selected_output = GeneratorOutputDialog(_default_output_file)
#     selected_output_options: OutputOptions = selected_output.get_selected_options()
#
#     # during test the tables might not get initialized so we do that here.
#     am_db = AnkiMorphsDB()
#     am_db.create_all_tables()
#
#     gd._background_generate_study_plan(selected_output_options)
#
#     with open(correct_output_file, encoding="utf8") as a, open(
#         test_output_file, encoding="utf8"
#     ) as b:
#
#         diff: dict[str, list] = compare(load_csv(a), load_csv(b))
#         pprint.pprint(diff)
#         assert len(diff) != 0
#         for changes in diff.values():
#             assert len(changes) == 0
#
#     os.remove(test_output_file)


################################################################
#            CASE: BIG JAPANESE COLLECTION
################################################################
# Checks the frequency files generated with using the am_db from
# the `big_japanese_collection.anki2`.
# The collection is arbitrary since the generators only use the
# found db.
################################################################
case_some_studied_japanese_inflections = FakeEnvironmentParams(
    collection="some_studied_japanese_collection",
    config=config_inflection_evaluation,
    am_db="some_studied_japanese.db",
)

case_some_studied_japanese_lemmas = FakeEnvironmentParams(
    collection="some_studied_japanese_collection",
    config=config_lemma_evaluation,
    am_db="some_studied_japanese.db",
)


@pytest.mark.debug
@pytest.mark.parametrize(
    "fake_environment, unique_known_number, unique_known_percent, total_known_number, total_known_percent",
    [
        (case_some_studied_japanese_inflections, "3", "0.6 %", "44", "2.7 %"),
        (case_some_studied_japanese_lemmas, "16", "3.3 %", "83", "5.0 %"),
    ],
    indirect=["fake_environment"],
)
def test_readability_report(  # pylint:disable=too-many-arguments
    fake_environment: FakeEnvironment,
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

    gw._background_generate_report()

    _row = 1
    _item: QTableWidgetItem | None

    _item = gw.ui.numericalTableWidget.item(_row, gw._file_name_column)
    assert _item is not None
    assert _item.text() == "Black Clover - 002 - The Boys` Promise [shiRo].jp.srt"

    _item = gw.ui.percentTableWidget.item(_row, gw._file_name_column)
    assert _item is not None
    assert _item.text() == "Black Clover - 002 - The Boys` Promise [shiRo].jp.srt"

    _item = gw.ui.numericalTableWidget.item(_row, gw._unique_morphs_column)
    assert _item is not None
    assert _item.text() == "482"

    _item = gw.ui.percentTableWidget.item(_row, gw._unique_morphs_column)
    assert _item is not None
    assert _item.text() == "482"

    _item = gw.ui.numericalTableWidget.item(_row, gw._unique_known_column)
    assert _item is not None
    assert _item.text() == unique_known_number

    _item = gw.ui.percentTableWidget.item(_row, gw._unique_known_column)
    assert _item is not None
    assert _item.text() == unique_known_percent

    _item = gw.ui.numericalTableWidget.item(_row, gw._total_morphs_column)
    assert _item is not None
    assert _item.text() == "1656"

    _item = gw.ui.percentTableWidget.item(_row, gw._total_morphs_column)
    assert _item is not None
    assert _item.text() == "1656"

    _item = gw.ui.numericalTableWidget.item(_row, gw._total_known_column)
    assert _item is not None
    assert _item.text() == total_known_number

    _item = gw.ui.percentTableWidget.item(_row, gw._total_known_column)
    assert _item is not None
    assert _item.text() == total_known_percent
