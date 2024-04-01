import json
import os
import pprint
import sys
from pathlib import Path
from unittest import mock

import aqt
import pytest
from csv_diff import compare, load_csv

from ankimorphs import (
    AnkiMorphsDB,
    ankimorphs_config,
    ankimorphs_db,
    generators_window,
    spacy_wrapper,
)
from ankimorphs.generators_output_dialog import GeneratorOutputDialog, OutputOptions
from ankimorphs.generators_window import GeneratorWindow


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    mock_mw = mock.Mock(spec=aqt.mw)

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    fake_morphemizers_path = os.path.join(tests_path, "morphemizers")

    _config_data = None
    with open(os.path.join(tests_path, "meta.json"), encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.pm.profileFolder.return_value = tests_path
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data["config"]

    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    morph_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_gd_mw = mock.patch.object(generators_window, "mw", mock_mw)

    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    sys.path.append(fake_morphemizers_path)
    patch_config_mw.start()
    morph_db_mw.start()
    patch_gd_mw.start()
    patch_testing_variable.start()

    yield

    patch_config_mw.stop()
    patch_gd_mw.stop()
    morph_db_mw.stop()
    patch_testing_variable.stop()
    sys.path.remove(fake_morphemizers_path)


def test_frequency_file_generator_spacy(  # pylint:disable=unused-argument, too-many-locals
    fake_environment, qtbot
):
    gd = GeneratorWindow()

    input_folder = os.path.join("tests", "data", "ja_subs")
    test_output_file = os.path.join("tests", "data", "test_output_file.csv")
    correct_output_file = os.path.join(
        "tests", "data", "correct_outputs", "spacy_ja_sm_freq.csv"
    )

    gd.ui.inputDirLineEdit.setText(input_folder)
    gd._background_gather_files_and_populate_files_column(col=None)

    index = -1
    for _index, mizer in enumerate(gd._morphemizers):
        # print(f"mizer.get_description(): {mizer.get_description()}")
        if mizer.get_description() == "spaCy: ja_core_news_sm":
            index = _index

    # print(f"index: {index}")
    gd.ui.morphemizerComboBox.setCurrentIndex(index)

    _default_output_file = Path(test_output_file)
    selected_output = GeneratorOutputDialog(_default_output_file)
    selected_output_options: OutputOptions = selected_output.get_selected_options()

    gd._background_generate_frequency_file(selected_output_options)

    with open(correct_output_file, encoding="utf8") as a, open(
        test_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)
        assert len(diff) != 0
        for changes in diff.values():
            assert len(changes) == 0

    os.remove(test_output_file)


def test_frequency_file_generator_mecab(  # pylint:disable=unused-argument, too-many-locals
    fake_environment, qtbot
):
    gd = GeneratorWindow()

    input_folder = os.path.join("tests", "data", "ja_subs")
    test_output_file = os.path.join("tests", "data", "test_output_file_mecab.csv")
    correct_output_file = os.path.join(
        "tests", "data", "correct_outputs", "mecab_ja_sm_freq.csv"
    )

    gd.ui.inputDirLineEdit.setText(input_folder)
    gd._background_gather_files_and_populate_files_column(col=None)

    index = -1
    for _index, mizer in enumerate(gd._morphemizers):
        # print(f"mizer.get_description(): {mizer.get_description()}")
        if mizer.get_description() == "AnkiMorphs: Japanese":
            index = _index

    # print(f"index: {index}")
    gd.ui.morphemizerComboBox.setCurrentIndex(index)

    _default_output_file = Path(test_output_file)
    selected_output = GeneratorOutputDialog(_default_output_file)
    selected_output_options: OutputOptions = selected_output.get_selected_options()

    gd._background_generate_frequency_file(selected_output_options)

    with open(correct_output_file, encoding="utf8") as a, open(
        test_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)
        assert len(diff) != 0
        for changes in diff.values():
            assert len(changes) == 0

    os.remove(test_output_file)


def test_study_plan_generator(  # pylint:disable=unused-argument, too-many-locals
    fake_environment, qtbot
):
    gd = GeneratorWindow()

    input_folder = os.path.join("tests", "data", "ja_subs")
    test_output_file = os.path.join("tests", "data", "mecab_study_plan_test_output.csv")
    correct_output_file = os.path.join(
        "tests", "data", "correct_outputs", "mecab_study_plan.csv"
    )

    gd.ui.inputDirLineEdit.setText(input_folder)
    gd._background_gather_files_and_populate_files_column(col=None)

    index = -1
    for _index, mizer in enumerate(gd._morphemizers):
        # print(f"mizer.get_description(): {mizer.get_description()}")
        if mizer.get_description() == "AnkiMorphs: Japanese":
            index = _index

    # print(f"index: {index}")
    gd.ui.morphemizerComboBox.setCurrentIndex(index)

    _default_output_file = Path(test_output_file)
    selected_output = GeneratorOutputDialog(_default_output_file)
    selected_output_options: OutputOptions = selected_output.get_selected_options()

    # during tests the tables might not get initialized so we do that here.
    am_db = AnkiMorphsDB()
    am_db.create_all_tables()

    gd._background_generate_study_plan(selected_output_options)

    with open(correct_output_file, encoding="utf8") as a, open(
        test_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)
        assert len(diff) != 0
        for changes in diff.values():
            assert len(changes) == 0

    os.remove(test_output_file)
