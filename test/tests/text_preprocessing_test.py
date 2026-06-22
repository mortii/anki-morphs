from __future__ import annotations

import copy
from test.fake_configs import default_config_dict
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest

from ankimorphs import text_preprocessing
from ankimorphs.ankimorphs_config import AnkiMorphsConfig, RawConfigKeys

default_fake_environment = FakeEnvironmentParams()


@pytest.mark.parametrize(
    "fake_environment_fixture, preprocess_option, option_enabled, input_text, correct_output",
    [
        (
            default_fake_environment,
            "preprocess_ignore_bracket_contents",
            True,
            "[hello] world",
            " world",
        ),
        (
            default_fake_environment,
            "preprocess_ignore_bracket_contents",
            False,
            "[hello] world",
            "[hello] world",
        ),
        (
            default_fake_environment,
            "preprocess_ignore_round_bracket_contents",
            True,
            "（hello） world",
            " world",
        ),
        (
            default_fake_environment,
            "preprocess_ignore_round_bracket_contents",
            False,
            "（hello） world",
            "（hello） world",
        ),
        (
            default_fake_environment,
            "preprocess_ignore_slim_round_bracket_contents",
            True,
            "(hello) world",
            " world",
        ),
        (
            default_fake_environment,
            "preprocess_ignore_slim_round_bracket_contents",
            False,
            "(hello) world",
            "(hello) world",
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_preprocessing_square_brackets(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    preprocess_option: str,
    option_enabled: bool,
    input_text: str,
    correct_output: str,
) -> None:
    am_config = AnkiMorphsConfig()
    setattr(am_config, preprocess_option, option_enabled)
    processed_text: str = text_preprocessing.get_processed_text(am_config, input_text)
    assert processed_text == correct_output


@pytest.mark.parametrize(
    "fake_environment_fixture, input_text, correct_output",
    [
        pytest.param(
            FakeEnvironmentParams(
                config=copy.deepcopy(default_config_dict)
                | {
                    RawConfigKeys.PREPROCESS_IGNORE_CUSTOM_CHARACTERS: True,
                    RawConfigKeys.PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE: ",.?",
                },
            ),
            "world,.?",
            "world",
            id="preprocess_custom_chars",
        ),
        pytest.param(
            FakeEnvironmentParams(),
            "world,.?",
            "world,.?",
            id="no_preprocess",
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_preprocess_custom_characters(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    input_text: str,
    correct_output: str,
) -> None:
    am_config = AnkiMorphsConfig()
    text_preprocessing.update_translation_table()
    processed_text: str = text_preprocessing.get_processed_text(am_config, input_text)
    assert processed_text == correct_output
