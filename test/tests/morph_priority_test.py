from pathlib import Path
from test.fake_configs import config_inflection_evaluation, config_lemma_evaluation
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest

from ankimorphs import debug_utils
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.exceptions import FrequencyFileMalformedException
from ankimorphs.recalc import morph_priority_utils

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
    ],
    indirect=["fake_environment_fixture"],
)
def test_morph_priority_with_frequency_file(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    csv_file_name: str,
    only_lemma_priorities: bool,
    json_file_name: str,
) -> None:
    morph_priorities = morph_priority_utils._get_morph_frequency_file_priority(
        frequency_file_name=csv_file_name, only_lemma_priorities=only_lemma_priorities
    )

    json_file_path = Path(
        fake_environment_fixture.mock_mw.pm.profileFolder(),
        fake_environment_fixture.frequency_files_dir,
        json_file_name,
    )

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
    collection="lemma_evaluation_lemma_extra_fields_collection",
    config=config_lemma_evaluation,
    am_db="lemma_evaluation_lemma_extra_fields.db",
)

case_collection_frequency_inflection_params = FakeEnvironmentParams(
    collection="lemma_evaluation_lemma_extra_fields_collection",
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

    morph_priorities = morph_priority_utils._get_morph_priority(
        am_db=fake_environment_fixture.mock_db,
        am_config=am_config,
        am_config_filter=am_config.filters[0],
    )

    json_file_path = Path(
        fake_environment_fixture.mock_mw.pm.profileFolder(),
        fake_environment_fixture.frequency_files_dir,
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
    frequency_files_dir="wrong_inputs",
)


@pytest.mark.should_cause_exception
@pytest.mark.parametrize(
    "fake_environment_fixture, csv_file_name",
    [
        (case_no_headers_params, "frequency_file_no_headers.csv"),
    ],
    indirect=["fake_environment_fixture"],
)
def test_morph_priority_with_invalid_frequency_file(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment, csv_file_name: str
) -> None:
    try:
        morph_priority_utils._get_morph_frequency_file_priority(
            frequency_file_name=csv_file_name, only_lemma_priorities=True
        )
    except FrequencyFileMalformedException:
        pass
    else:
        assert False
