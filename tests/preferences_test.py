import json
from unittest import mock

import pytest

from ankimorphs import config, morph_utils


@pytest.fixture(
    scope="module"
)  # module-scope: created and destroyed once per module. Cached.
def fake_environment():
    mock_mw = mock.MagicMock(spec=preferences.mw)

    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.addonManager.getConfig.return_value = _config_data
    # mock_mw.addonManager = aqt.addons.AddonManager(mock_mw)
    patch_preferences_mw = mock.patch.object(preferences, "mw", mock_mw)
    patch_preferences_mw.start()
    yield
    patch_preferences_mw.stop()


def test_get_preference_in_config_py(fake_environment):
    assert preferences.get_config("threshold_mature") == 21


def test_ignore_square_brackets(fake_environment):
    sentence_1 = "[こんにちは]私の名前は[シャン]です。"
    case_1 = "私の名前はです。"

    assert preferences.get_config("Option_IgnoreBracketContents") is True
    assert morphemes.replace_bracket_contents(sentence_1) == case_1

    # preferences.update_preferences({"Option_IgnoreBracketContents": True})
    # assert morphemes.replace_bracket_contents(sentence_1) == case_1


def test_ignore_round_brackets_slim(fake_environment):
    sentence_1 = "(こんにちは)私の名前は(シャン)です。"
    case_1 = "私の名前はです。"

    assert preferences.get_config("Option_IgnoreSlimRoundBracketContents") is True
    assert morphemes.replace_bracket_contents(sentence_1) == case_1

    # preferences.update_preferences({"Option_IgnoreSlimRoundBracketContents": True})
    # assert morphemes.replace_bracket_contents(sentence_1) == case_1


def test_ignore_round_brackets_japanese(fake_environment):
    sentence_1 = "（こんにちは）私の名前は（シャン）です。"
    case_1 = "私の名前はです。"

    assert preferences.get_config("Option_IgnoreRoundBracketContents") is True
    assert morphemes.replace_bracket_contents(sentence_1) == case_1

    # preferences.update_preferences({"Option_IgnoreRoundBracketContents": True})
    # assert morphemes.replace_bracket_contents(sentence_1) == case_1
