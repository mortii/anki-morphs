from __future__ import annotations

from pathlib import Path
from test.fake_configs import config_inflection_evaluation, config_lemma_evaluation
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest

from ankimorphs import debug_utils, morph_priority_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.exceptions import PriorityFileMalformedException

# we don't need any special parameters for these tests
default_fake_environment_params = FakeEnvironmentParams()


@pytest.mark.parametrize(
    "fake_environment_fixture, csv_file_name, only_lemma_priorities, json_file_name",
    [
        (
            default_fake_environment_params,
            "ja_core_news_sm_freq_inflection_min_occurrence.csv",
            False,
            "ja_core_news_sm_freq_inflection_min_occurrence_inflection_priority.json",
        ),
        (
            default_fake_environment_params,
            "ja_core_news_sm_freq_inflection_min_occurrence.csv",
            True,
            "ja_core_news_sm_freq_inflection_min_occurrence_lemma_priority.json",
        ),
        (
            default_fake_environment_params,
            "ja_core_news_sm_freq_lemma_min_occurrence.csv",
            True,
            "ja_core_news_sm_freq_lemma_min_occurrence_lemma_priority.json",
        ),
        (
            default_fake_environment_params,
            "mecab_study_plan_lemma.csv",
            True,
            "mecab_study_plan_lemma_priority.json",
        ),
        (
            default_fake_environment_params,
            "mecab_study_plan_inflection.csv",
            False,
            "mecab_study_plan_inflection_priority.json",
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_morph_priority_with_priority_file(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment | None,
    csv_file_name: str,
    only_lemma_priorities: bool,
    json_file_name: str,
) -> None:
    """
    Checks if morph priorities are loaded correctly from the priority files.
    Creating json files can be done with 'save_to_json_file' from 'debug_utils.py'
    """

    if fake_environment_fixture is None:
        pytest.xfail()

    morph_priorities = morph_priority_utils._load_morph_priorities_from_file(
        priority_file_name=csv_file_name, only_lemma_priorities=only_lemma_priorities
    )

    json_file_path = Path(
        fake_environment_fixture.mock_mw.pm.profileFolder(),
        fake_environment_fixture.priority_files_dir,
        json_file_name,
    )

    # debug_utils.save_to_json_file(json_file_path, morph_priorities)

    correct_morphs_priorities = debug_utils.load_dict_from_json_file(json_file_path)
    assert len(correct_morphs_priorities) > 0
    assert morph_priorities == correct_morphs_priorities


################################################################
#                  CASE: COLLECTION FREQUENCY
################################################################
# Get the respective morph priorities based on the collection
# frequencies.
################################################################
case_collection_frequency_lemma_params = FakeEnvironmentParams(
    actual_col="lemma_evaluation_lemma_extra_fields_collection",
    expected_col="lemma_evaluation_lemma_extra_fields_collection",
    config=config_lemma_evaluation,
    am_db="lemma_evaluation_lemma_extra_fields.db",
)

case_collection_frequency_inflection_params = FakeEnvironmentParams(
    actual_col="lemma_evaluation_lemma_extra_fields_collection",
    expected_col="lemma_evaluation_lemma_extra_fields_collection",
    config=config_inflection_evaluation,
    am_db="lemma_evaluation_lemma_extra_fields.db",
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture, json_file_name",
    [
        (
            case_collection_frequency_lemma_params,
            "morph_priority_collection_frequency_lemma.json",
        ),
        (
            case_collection_frequency_inflection_params,
            "morph_priority_collection_frequency_inflection.json",
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_morph_priority_with_collection_frequency(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    json_file_name: str,
) -> None:
    am_config = AnkiMorphsConfig()

    morph_priorities = morph_priority_utils.get_morph_priority(
        am_db=fake_environment_fixture.mock_db,
        only_lemma_priorities=am_config.evaluate_morph_lemma,
        morph_priority_selection=am_config.filters[0].morph_priority_selection,
    )

    json_file_path = Path(
        fake_environment_fixture.mock_mw.pm.profileFolder(),
        fake_environment_fixture.priority_files_dir,
        json_file_name,
    )

    correct_morphs_priorities = debug_utils.load_dict_from_json_file(json_file_path)
    assert len(correct_morphs_priorities) > 0
    assert morph_priorities == correct_morphs_priorities


################################################################
#                    CASE: NO HEADERS
################################################################
# The file 'frequency_file_no_headers.csv' has no headers and
# should raise an exception
################################################################
case_no_headers_params = FakeEnvironmentParams(
    priority_files_dir="wrong_inputs",
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture, csv_file_name, only_lemma_priorities",
    [
        (case_no_headers_params, "priority_file_no_headers.csv", True),
        (
            default_fake_environment_params,
            "mecab_study_plan_inflection.csv",
            True,
        ),
        (
            default_fake_environment_params,
            "mecab_study_plan_lemma.csv",
            False,
        ),
        (
            default_fake_environment_params,
            "ja_core_news_sm_freq_lemma_min_occurrence.csv",
            False,
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_morph_priority_with_invalid_priority_file(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    csv_file_name: str,
    only_lemma_priorities: bool,
) -> None:
    try:
        morph_priority_utils._load_morph_priorities_from_file(
            priority_file_name=csv_file_name,
            only_lemma_priorities=only_lemma_priorities,
        )
    except PriorityFileMalformedException:
        pass
    else:
        assert False
