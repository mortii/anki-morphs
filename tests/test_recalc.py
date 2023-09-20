from unittest import mock

import pytest

from ankimorphs import recalc, preferences, morph_stats
from tests.fake_config import FakeConfig
from tests.fake_preferences import get_fake_preferences


@pytest.fixture(
    scope="module"
)  # module-scope: created and destroyed once per module. Cached.
def fake_environment():
    mock_mw = mock.MagicMock(spec=recalc.mw)
    mock_mw.col.get_config.return_value = get_fake_preferences()

    mock_config_py = FakeConfig()

    patch_recalc_mw = mock.patch.object(recalc, "mw", mock_mw)
    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)
    patch_morph_stats_mw = mock.patch.object(morph_stats, "mw", mock_mw)
    patch_preferences_config_py = mock.patch.object(
        preferences, "config_py", mock_config_py
    )

    patch_recalc_mw.start()
    patch_preferences_mw.start()
    patch_morph_stats_mw.start()
    patch_preferences_config_py.start()

    yield

    patch_recalc_mw.stop()
    patch_preferences_mw.stop()
    patch_morph_stats_mw.stop()
    patch_preferences_config_py.stop()


def mock_get_config_py_preference(key):
    return FakeConfig().default[key]


def test_recalc(fake_environment):
    mock_collection = mock.MagicMock()

    recalc.main_background_op(mock_collection)

    assert True
