import os
import pprint
from pathlib import Path

import pytest
from csv_diff import compare, load_csv

from ankimorphs import AnkiMorphsDB
from ankimorphs.generators_output_dialog import GeneratorOutputDialog, OutputOptions
from ankimorphs.generators_window import GeneratorWindow

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    TESTS_DATA_CORRECT_OUTPUTS_PATH,
    TESTS_DATA_PATH,
    TESTS_DATA_TESTS_OUTPUTS_PATH,
    config_big_japanese_collection,
    fake_environment,
)


# when stacking 'parametrize' we run the function with all permutations
@pytest.mark.parametrize(
    "fake_environment",
    [("big-japanese-collection", config_big_japanese_collection)],
    indirect=True,
)
@pytest.mark.parametrize(
    "morphemizer_description",
    ["spaCy: ja_core_news_sm", "AnkiMorphs: Japanese"],
)
@pytest.mark.parametrize(
    "full_format",
    [True, False],
)
def test_frequency_file_generator(  # pylint:disable=unused-argument, too-many-locals
    fake_environment, morphemizer_description, full_format, qtbot
):
    gw = GeneratorWindow()

    input_folder = Path(TESTS_DATA_PATH, "ja_subs")
    test_output_file = Path(TESTS_DATA_TESTS_OUTPUTS_PATH, "test_output_file.csv")

    if morphemizer_description == "AnkiMorphs: Japanese":
        if full_format:
            _file_name = "mecab_freq_full.csv"
        else:
            _file_name = "mecab_freq_min.csv"
    else:
        if full_format:
            _file_name = "ja_core_news_sm_freq_full.csv"
        else:
            _file_name = "ja_core_news_sm_freq_min.csv"

    correct_output_file = Path(
        TESTS_DATA_CORRECT_OUTPUTS_PATH,
        _file_name,
    )

    print(f"loaded file: {correct_output_file}")

    gw.ui.inputDirLineEdit.setText(str(input_folder))
    gw._background_gather_files_and_populate_files_column(col=None)

    index = -1
    for _index, mizer in enumerate(gw._morphemizers):
        # print(f"mizer.get_description(): {mizer.get_description()}")
        if mizer.get_description() == morphemizer_description:
            index = _index

    # print(f"index: {index}")
    gw.ui.morphemizerComboBox.setCurrentIndex(index)

    _default_output_file = test_output_file
    selected_output = GeneratorOutputDialog(_default_output_file)
    selected_output.ui.addOccurrencesColumnCheckBox.setChecked(True)

    if not full_format:
        # To minimize the permutations we use the "comprehension" option along with the minimum
        # format, so we test both of those at the same time.
        selected_output.ui.storeOnlyMorphLemmaRadioButton.setChecked(True)
        selected_output.ui.storeMorphLemmaAndInflectionRadioButton.setChecked(False)
        selected_output.ui.comprehensionRadioButton.setChecked(True)

    selected_output_options: OutputOptions = selected_output.get_selected_options()

    gw._background_generate_frequency_file(selected_output_options)

    with open(correct_output_file, encoding="utf8") as a, open(
        test_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)
        assert len(diff) != 0
        for changes in diff.values():
            assert len(changes) == 0

    os.remove(test_output_file)


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
