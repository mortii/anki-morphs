import json
import os
import shutil
from unittest import mock

import pytest
from aqt import setupLangAndBackend

from ankimorphs import config, get_config, morph_db, morph_stats, old_recalc

from anki.collection import Collection  # isort:skip pylint:disable=wrong-import-order


@pytest.fixture(
    scope="module"
)  # module-scope: created and destroyed once per module. Cached.
def fake_environment():
    tests_path = os.path.join(os.path.abspath("tests"), "data")
    collection_path_original = os.path.join(tests_path, "collection.anki2")
    collection_path_duplicate = os.path.join(tests_path, "duplicate_collection.anki2")
    collection_path_duplicate_media = os.path.join(
        tests_path, "duplicate_collection.media"
    )

    # If dst already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)

    mock_mw = mock.Mock(spec=preferences.mw)  # can use any mw to spec
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )

    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.addonManager.getConfig.return_value = _config_data

    mock_mw.pm.profileFolder.return_value = os.path.join(
        os.path.abspath("tests"), "data"
    )

    # path = os.path.join(aqt.mw.pm.profileFolder(), "dbs", file_name)

    patch_recalc_mw = mock.patch.object(recalc, "mw", mock_mw)
    morph_db_mw = mock.patch.object(morph_db, "mw", mock_mw)
    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)
    patch_morph_stats_mw = mock.patch.object(morph_stats, "mw", mock_mw)

    patch_get_modify_enabled_models = mock.patch(
        "ankimorphs.recalc.get_modify_enabled_models",
        lambda: ({"morphman_sub2srs"}, False),
    )

    patch_get_filter_by_mid_and_tags = mock.patch(
        "ankimorphs.recalc.get_filter_by_mid_and_tags",
        lambda x, tags: {
            "Type": "morphman_sub2srs",
            "Tags": [],
            "Fields": ["Japanese"],
            "Morphemizer": "MecabMorphemizer",
            "Read": True,
            "Modify": True,
        },
    )

    patch_recalc_mw.start()
    morph_db_mw.start()
    patch_preferences_mw.start()
    patch_morph_stats_mw.start()
    patch_get_modify_enabled_models.start()
    patch_get_filter_by_mid_and_tags.start()

    yield mock_mw.col

    tests_path = os.path.join(mock_mw.pm.profileFolder())
    db_path = os.path.join(mock_mw.pm.profileFolder(), "dbs")

    os.remove(os.path.join(db_path, get_config("path_all")))
    os.remove(os.path.join(db_path, get_config("path_known")))
    os.remove(os.path.join(db_path, get_config("path_mature")))
    os.remove(os.path.join(db_path, get_config("path_seen")))
    os.remove(os.path.join(tests_path, get_config("path_stats")))

    mock_mw.col.close()

    patch_recalc_mw.stop()
    morph_db_mw.stop()
    patch_preferences_mw.stop()
    patch_morph_stats_mw.stop()
    patch_get_modify_enabled_models.stop()
    patch_get_filter_by_mid_and_tags.stop()

    os.remove(collection_path_duplicate)
    shutil.rmtree(collection_path_duplicate_media)


def test_recalc(fake_environment):
    mock_collection = fake_environment
    recalc.main_background_op(mock_collection)
    assert False
