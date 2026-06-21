import json
import os
from collections.abc import Iterator
from unittest import mock

import aqt
import pytest

from ankimorphs import ankimorphs_config
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizers import camel_wrapper
from ankimorphs.morphemizers.camel_morphemizer import CamelMorphemizer


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment_fixture() -> Iterator[None]:
    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.pm.profileFolder.return_value = os.path.join("test", "data")
    mock_mw.addonManager.getConfig.return_value = _config_data

    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_camel_wrapper_mw = mock.patch.object(camel_wrapper, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        camel_wrapper, "testing_environment", True
    )

    patch_config_mw.start()
    patch_camel_wrapper_mw.start()
    patch_testing_variable.start()

    yield

    patch_config_mw.stop()
    patch_camel_wrapper_mw.stop()
    patch_testing_variable.stop()


@pytest.mark.parametrize(
    "db_name, sentence, expected_am_morphs",
    [
        (
            "calima-msa-r13",  # Modern Standard Arabic
            # "The boy went to the school"
            "ذهب الولد إلى المدرسة",
            [
                Morpheme(lemma="ذَهَب", inflection="ذهب"),
                Morpheme(lemma="وَلَد", inflection="الولد"),
                Morpheme(lemma="إِلَى", inflection="إلى"),
                Morpheme(lemma="مَدْرَسَة", inflection="المدرسة"),
            ],
        ),
        (
            "calima-egy-r13",  # Egyptian Arabic
            # "The boy went to the school" (Egyptian dialect)
            "الواد راح المدرسة",
            [
                Morpheme(lemma="واد", inflection="الواد"),
                Morpheme(lemma="راح", inflection="راح"),
                Morpheme(lemma="مَدْرَسَة", inflection="المدرسة"),
            ],
        ),
        (
            "calima-glf-01",  # Gulf Arabic
            # "The boy went to the school" (Gulf dialect)
            "الولد راح المدرسة",
            [
                Morpheme(lemma="وَلَد", inflection="الولد"),
                Morpheme(lemma="راح", inflection="راح"),
                Morpheme(lemma="مَدرَسَة", inflection="المدرسة"),
            ],
        ),
    ],
)
def test_camel(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
    db_name: str,
    sentence: str,
    expected_am_morphs: list[Morpheme],
) -> None:
    camel_wrapper.load_camel_modules()

    if not camel_wrapper.successful_import:
        pytest.skip("CAMeL Tools is not installed")

    morphemizer = CamelMorphemizer(db_name)

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True

    processed_morphs: list[Morpheme] = next(
        morphemizer.get_processed_morphs(am_config, [sentence])
    )

    assert len(processed_morphs) == len(expected_am_morphs)

    for index, morph in enumerate(processed_morphs):
        expected = expected_am_morphs[index]
        assert morph.inflection == expected.inflection, (
            f"inflection mismatch at index {index}: "
            f"got {morph.inflection!r}, expected {expected.inflection!r}"
        )
        assert morph.lemma == expected.lemma, (
            f"lemma mismatch at index {index}: "
            f"got {morph.lemma!r}, expected {expected.lemma!r}"
        )


@pytest.mark.parametrize("db_name", ["calima-msa-r13", "calima-egy-r13", "calima-glf-01"])
def test_camel_oov_token_does_not_crash(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
    db_name: str,
) -> None:
    # Regression test for the Python 3.13 crash: camel-tools 1.6.0's NOAN backoff
    # path calls re.sub() with an out-of-vocabulary stem as the *replacement
    # template*. A stem ending in a backslash raised
    # `re.error: bad escape (end of pattern)` under Python 3.13's stricter parser,
    # aborting priority-file generation on any corpus containing such tokens.
    #
    # The morphemizer now uses backoff="NONE" (so this path is unreachable) plus a
    # try/except re.error safety net. Either alone prevents the crash; this test
    # guards both. The token below is exactly the input that reproduced the crash.
    camel_wrapper.load_camel_modules()

    if not camel_wrapper.successful_import:
        pytest.skip("CAMeL Tools is not installed")

    morphemizer = CamelMorphemizer(db_name)
    am_config = AnkiMorphsConfig()

    # "ا\\" is a single token: Arabic alef followed by a trailing backslash.
    # Real Egyptian words in the same sentence must still be processed normally.
    sentence = "البيت ا\\ المدرسة"

    # Must not raise (previously raised re.error mid-iteration).
    processed_morphs: list[Morpheme] = next(
        morphemizer.get_processed_morphs(am_config, [sentence])
    )

    # The OOV backslash token is skipped; the surrounding real words survive.
    inflections = {morph.inflection for morph in processed_morphs}
    assert "ا\\" not in inflections
    assert "البيت" in inflections
