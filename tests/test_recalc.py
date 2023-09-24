import json
import os
from unittest import mock

import pytest

from ankimorphs import get_preference, morph_db, morph_stats, preferences, recalc


@pytest.fixture(
    scope="module"
)  # module-scope: created and destroyed once per module. Cached.
def fake_environment():
    mock_mw = mock.MagicMock(spec=recalc.mw)

    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.addonManager.getConfig.return_value = _config_data
    mock_mw.pm.profileFolder.return_value = os.path.abspath("tests")

    # path = os.path.join(aqt.mw.pm.profileFolder(), "dbs", file_name)

    patch_recalc_mw = mock.patch.object(recalc, "mw", mock_mw)
    morph_db_mw = mock.patch.object(morph_db, "mw", mock_mw)
    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)
    patch_morph_stats_mw = mock.patch.object(morph_stats, "mw", mock_mw)

    patch_recalc_mw.start()
    morph_db_mw.start()
    patch_preferences_mw.start()
    patch_morph_stats_mw.start()

    yield

    tests_path = os.path.join(mock_mw.pm.profileFolder())
    db_path = os.path.join(mock_mw.pm.profileFolder(), "dbs")

    os.remove(os.path.join(db_path, get_preference("path_all")))
    os.remove(os.path.join(db_path, get_preference("path_known")))
    os.remove(os.path.join(db_path, get_preference("path_mature")))
    os.remove(os.path.join(db_path, get_preference("path_seen")))
    os.remove(os.path.join(tests_path, get_preference("path_stats")))

    patch_recalc_mw.stop()
    morph_db_mw.stop()
    patch_preferences_mw.stop()
    patch_morph_stats_mw.stop()


def test_recalc(fake_environment):
    mock_collection = mock.MagicMock()
    recalc.main_background_op(mock_collection)
    assert True
