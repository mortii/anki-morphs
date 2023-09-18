from unittest import mock

import pytest

from aqt.reviewer import Reviewer

from morph import recalc, preferences, morph_stats, reviewing_utils
from tests.fake_config import FakeConfig
from tests.fake_preferences import get_fake_preferences


@pytest.fixture(scope="module")  # module-scope: created and destroyed once per module. Cached.
def fake_environment():

    mock_reviewer = mock.MagicMock(pec=Reviewer)  # todo, mocking too much
    mock_reviewer.mw.col.sched.version.__int__.return_value = 'foobarbaz'

    mock_preferences_mw = mock.MagicMock(spec=preferences.mw)
    mock_preferences_mw.col.sched.version.__str__.return_value = 'foobarbaz'

    # mock_reviewer.mw.col.get_config.return_value = get_fake_preferences()

    mock_config_py = FakeConfig()

    patch_init_reviewer = mock.patch.object(reviewing_utils, 'Reviewer', mock_reviewer)
    patch_preferences_mw = mock.patch.object(preferences, 'mw', mock_preferences_mw)
    patch_preferences_config_py = mock.patch.object(preferences, 'config_py', mock_config_py)

    patch_init_reviewer.start()
    patch_preferences_mw.start()
    patch_preferences_config_py.start()

    yield

    patch_init_reviewer.stop()
    patch_preferences_mw.stop()
    patch_preferences_config_py.stop()


def mock_get_config_py_preference(key):
    return FakeConfig().default[key]


def test_next_card(fake_environment):
    mock_reviewer = mock.MagicMock()
    mock_old_next_card = mock.MagicMock()

    reviewing_utils.my_next_card(mock_reviewer, mock_old_next_card)


    assert True
