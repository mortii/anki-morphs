from __future__ import annotations

from test.fake_configs import config_ignoring_custom_characters
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest

from ankimorphs import text_preprocessing
from ankimorphs.ankimorphs_config import AnkiMorphsConfig

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


################################################################
#               CASE: IGNORING CUSTOM CHARACTERS
################################################################
# Config contains has 'PREPROCESS_IGNORE_CUSTOM_CHARACTERS' = True,
# and 'PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE' = ",.?"
# Database choice is arbitrary.
# Collection choice is arbitrary
################################################################
case_ignoring_custom_characters_params = FakeEnvironmentParams(
    config=config_ignoring_custom_characters,
)


@pytest.mark.parametrize(
    "fake_environment_fixture, input_text, correct_output",
    [
        (
            case_ignoring_custom_characters_params,
            "world,.?",
            "world",
        ),
        (
            default_fake_environment,
            "world,.?",
            "world,.?",
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
