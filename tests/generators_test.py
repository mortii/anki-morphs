import os
from unittest import mock

import aqt
import pytest
from csv_diff import compare, load_csv

from ankimorphs import FrequencyFileGeneratorDialog
from ankimorphs import frequency_file_generator as ffg
from ankimorphs import generator_dialog as gd
from ankimorphs.morphemizer import SpacyMorphemizer


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    print("fake environment initiated")
    mock_mw = mock.Mock(spec=aqt.mw)  # can use any mw to spec

    mock_mw.pm.profileFolder.return_value = os.path.join("tests", "data")
    mock_mw.progress.want_cancel.return_value = False

    patch_gd_mw = mock.patch.object(gd, "mw", mock_mw)
    patch_ffg_mw = mock.patch.object(ffg, "mw", mock_mw)

    patch_gd_mw.start()
    patch_ffg_mw.start()

    yield

    patch_gd_mw.stop()
    patch_ffg_mw.stop()


def test_frequency_file_generator(fake_environment, qtbot):
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

    diff: dict[str, list] = compare(
        load_csv(open(output_file, encoding="utf8")),
        load_csv(open(result_output_file, encoding="utf8")),
    )

    for changes in diff.values():
        assert len(changes) == 0

    os.remove(result_output_file)
