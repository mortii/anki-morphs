from unittest import mock

import pytest

from ankimorphs import morphemes, preferences
from tests.fake_config import FakeConfig
from tests.fake_preferences import get_fake_preferences


@pytest.fixture(
    scope="module"
)  # module-scope: created and destroyed once per module. Cached.
def fake_environment():
    mock_config_py = FakeConfig()

    mock_mw = mock.MagicMock(spec=preferences.mw)
    mock_mw.col.get_config.return_value = get_fake_preferences()

    # Replace the objects in the preferences module
    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)
    patch_preferences_config_py = mock.patch.object(
        preferences, "config_py", mock_config_py
    )

    patch_preferences_mw.start()
    patch_preferences_config_py.start()

    yield

    patch_preferences_mw.stop()
    patch_preferences_config_py.stop()


def test_get_preference_in_config_py(fake_environment):
    assert preferences.get_preference("threshold_mature") == 21


def test_get_non_existing_preference(fake_environment):
    assert preferences.get_preference("non existing preference") is None


def test_ignore_square_brackets(fake_environment):
    sentence_1 = "[こんにちは]私の名前は[シャン]です。"
    case_1 = "私の名前はです。"

    assert preferences.get_preference("Option_IgnoreBracketContents") is False
    assert morphemes.replaceBracketContents(sentence_1) == sentence_1

    preferences.update_preferences({"Option_IgnoreBracketContents": True})
    assert morphemes.replaceBracketContents(sentence_1) == case_1


def test_ignore_round_brackets_slim(fake_environment):
    sentence_1 = "(こんにちは)私の名前は(シャン)です。"
    case_1 = "私の名前はです。"

    assert preferences.get_preference("Option_IgnoreSlimRoundBracketContents") is False
    assert morphemes.replaceBracketContents(sentence_1) == sentence_1

    preferences.update_preferences({"Option_IgnoreSlimRoundBracketContents": True})
    assert morphemes.replaceBracketContents(sentence_1) == case_1


def test_ignore_round_brackets_japanese(fake_environment):
    sentence_1 = "（こんにちは）私の名前は（シャン）です。"
    case_1 = "私の名前はです。"

    assert preferences.get_preference("Option_IgnoreRoundBracketContents") is False
    assert morphemes.replaceBracketContents(sentence_1) == sentence_1

    preferences.update_preferences({"Option_IgnoreRoundBracketContents": True})
    assert morphemes.replaceBracketContents(sentence_1) == case_1
