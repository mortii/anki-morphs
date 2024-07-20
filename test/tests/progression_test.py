from __future__ import annotations

from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)
from typing import Any

import pytest
from aqt.qt import QTableWidgetItem  # pylint:disable=no-name-in-module

from ankimorphs.exceptions import NoMorphsInPriorityRangeException
from ankimorphs.progression.progression_window import ProgressionWindow

################################################################
# Checks if progression is properly reported with a specified
# db/collection and the various evaluation/statistics options;
# various table entries are checked.
################################################################

case_big_japanese_collection_params = FakeEnvironmentParams(
    am_db="big_japanese_collection.db", collection="big_japanese_collection"
)

case_some_studied_japanese_params = FakeEnvironmentParams(
    collection="some_studied_japanese_collection",
    am_db="some_studied_japanese.db",
)


@pytest.mark.parametrize(
    "fake_environment_fixture, evaluate_lemmas, priority_mode,"  # inputs
    "cumulative, min_priority, max_priority, bin_size,"  # inputs
    "k_priority_range, k_unique_morphs, k_total_known,"  # knowns
    "k_percent_unknown, k_lemma_list, k_inflection_list,"  # knowns
    "k_morph_statuses",  # knowns
    [
        (
            case_big_japanese_collection_params,  # fake_environment_fixture
            True,  # evaluate_lemmas
            "Collection frequency",  # priority_mode
            False,  # cumulative
            1,  # min_priority
            50000,  # max_priority
            500,  # bin_size
            "11501-12000",  # k_priority_range
            357,  # k_unique_morphs
            0,  # k_total_known
            "100.0 %",  # k_percent_unknown
            ["の", "は", "た"],  # k_lemma_list
            ["-", "-", "-"],  # k_inflection_list
            ["unknown", "unknown", "unknown"],  # k_morph_statuses
        ),
        (
            case_big_japanese_collection_params,  # fake_environment_fixture
            False,  # evaluate_lemmas
            "Collection frequency",  # priority_mode
            True,  # cumulative
            1001,  # min_priority
            1500,  # max_priority
            1600,  # bin_size
            "1001-1500",  # k_priority_range
            500,  # k_unique_morphs
            0,  # k_total_known
            "100.0 %",  # k_percent_unknown
            ["難しい", "面白い", "頑張る"],  # k_lemma_list
            ["難しい", "面白い", "頑張れ"],  # k_inflection_list
            ["unknown", "unknown", "unknown"],  # k_morph_statuses
        ),
        (
            case_some_studied_japanese_params,  # fake_environment_fixture
            True,  # evaluate_lemmas
            "ja_core_news_sm_freq_inflection_min_occurrence.csv",  # priority_mode
            False,  # cumulative
            1,  # min_priority
            500,  # max_priority
            100,  # bin_size
            "401-500",  # k_priority_range
            100,  # k_unique_morphs
            4,  # k_total_known
            "0.0 %",  # k_percent_unknown
            ["の", "に", "は"],  # k_lemma_list
            ["-", "-", "-"],  # k_inflection_list
            ["missing", "missing", "learning"],  # k_morph_statuses
        ),
        (
            case_some_studied_japanese_params,  # fake_environment_fixture
            False,  # evaluate_lemmas
            "ja_core_news_sm_freq_inflection_min_occurrence.csv",  # priority_mode
            True,  # cumulative
            1,  # min_priority
            10,  # max_priority
            100,  # bin_size
            "1-10",  # k_priority_range
            10,  # k_unique_morphs
            0,  # k_total_known
            "0.0 %",  # k_percent_unknown
            ["だ", "に", "は"],  # k_lemma_list
            ["だ", "に", "は"],  # k_inflection_list
            ["missing", "missing", "learning"],  # k_morph_statuses
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_progression(  # pylint:disable=too-many-arguments, unused-argument, too-many-locals too-many-statements
    fake_environment_fixture: FakeEnvironment,
    evaluate_lemmas: bool,
    priority_mode: str,
    cumulative: bool,
    min_priority: int,
    max_priority: int,
    bin_size: int,
    k_priority_range: str,
    k_unique_morphs: int,
    k_total_known: int,
    k_percent_unknown: str,
    k_lemma_list: list[str],
    k_inflection_list: list[str],
    k_morph_statuses: list[str],
    qtbot: Any,
) -> None:

    # Set window and options
    pw = ProgressionWindow()
    pw.ui.lemmaRadioButton.setChecked(evaluate_lemmas)
    pw.ui.inflectionRadioButton.setChecked(not evaluate_lemmas)
    pw.ui.morphPriorityCBox.setCurrentText(priority_mode)
    pw.ui.cumulativeCheckBox.setChecked(cumulative)
    pw.ui.minPrioritySpinBox.setValue(min_priority)
    pw.ui.maxPrioritySpinBox.setValue(max_priority)
    pw.ui.binSizeSpinBox.setValue(bin_size)

    # Calculate progress
    try:
        pw._background_calculate_progress_and_populate_tables()
    except NoMorphsInPriorityRangeException:
        print("raised NoMorphsInPriorityRangeException")

    # Compare to known output
    _item: QTableWidgetItem | None

    _row = pw.ui.numericalTableWidget.rowCount() - 1
    _column = 0
    _item = pw.ui.numericalTableWidget.item(_row, _column)
    assert _item is not None
    assert _item.text() == k_priority_range

    _row = pw.ui.numericalTableWidget.rowCount() - 1
    _column = 1
    _item = pw.ui.numericalTableWidget.item(_row, _column)
    assert _item is not None
    assert int(_item.text()) == k_unique_morphs

    _row = 0
    _column = 2
    _item = pw.ui.numericalTableWidget.item(_row, _column)
    assert _item is not None
    assert int(_item.text()) == k_total_known

    _row = 0
    _column = 4
    _item = pw.ui.percentTableWidget.item(_row, _column)
    assert _item is not None
    assert _item.text() == k_percent_unknown

    _lemma_list: list[str] = []
    for _row in [0, 1, 2]:
        _column = 1
        _item = pw.ui.morphTableWidget.item(_row, _column)
        assert _item is not None
        _lemma_list.append(_item.text())
    assert _lemma_list == k_lemma_list

    _inflection_list: list[str] = []
    for _row in [0, 1, 2]:
        _column = 2
        _item = pw.ui.morphTableWidget.item(_row, _column)
        assert _item is not None
        _inflection_list.append(_item.text())
    assert _inflection_list == k_inflection_list

    _morph_statuses: list[str] = []
    for _row in [0, 1, 2]:
        _column = 3
        _item = pw.ui.morphTableWidget.item(_row, _column)
        assert _item is not None
        _morph_statuses.append(_item.text())
    assert _morph_statuses == k_morph_statuses
