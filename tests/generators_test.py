import os
import pprint
import sys
from unittest import mock

import aqt
import pytest
from csv_diff import compare, load_csv

from ankimorphs import FrequencyFileGeneratorDialog
from ankimorphs import frequency_file_generator as ffg
from ankimorphs import generator_dialog as gd
from ankimorphs import spacy_wrapper


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    mock_mw = mock.Mock(spec=aqt.mw)

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    fake_morphemizers_path = os.path.join(tests_path, "morphemizers")

    mock_mw.pm.profileFolder.return_value = tests_path
    mock_mw.progress.want_cancel.return_value = False

    patch_gd_mw = mock.patch.object(gd, "mw", mock_mw)
    patch_ffg_mw = mock.patch.object(ffg, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    sys.path.append(fake_morphemizers_path)
    patch_gd_mw.start()
    patch_ffg_mw.start()
    patch_testing_variable.start()

    yield

    patch_gd_mw.stop()
    patch_ffg_mw.stop()
    patch_testing_variable.stop()
    sys.path.remove(fake_morphemizers_path)


def test_frequency_file_generator(  # pylint:disable=unused-argument
    fake_environment, qtbot
):
    ffgd = FrequencyFileGeneratorDialog()

    input_folder = os.path.join("tests", "data", "ja_subs")
    result_output_file = os.path.join("tests", "data", "ja_ffg_test_result.csv")

    ffgd.ui.inputDirLineEdit.setText(input_folder)
    ffgd.ui.outputFileLineEdit.setText(result_output_file)

    index = -1
    for _index, mizer in enumerate(ffgd._morphemizers):
        print(f"mizer.get_description(): {mizer.get_description()}")
        if mizer.get_description() == "spaCy: ja_core_news_sm":
            index = _index

    print(f"index: {index}")
    ffgd.ui.comboBox.setCurrentIndex(index)
    ffgd._background_generate_frequency_file(col=None)
    output_file = os.path.join("tests", "data", "ja_subs_correct_output.csv")

    with open(output_file, encoding="utf8") as a, open(
        result_output_file, encoding="utf8"
    ) as b:
        diff: dict[str, list] = compare(load_csv(a), load_csv(b))
        pprint.pprint(diff)
        assert len(diff) != 0
        for changes in diff.values():
            assert len(changes) == 0

    os.remove(result_output_file)
