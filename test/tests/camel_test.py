import json
import os
from collections.abc import Iterator
from unittest import mock

import aqt
import pytest

from ankimorphs import ankimorphs_config, name_file_utils
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
    # name_file_utils.mw is used by the ignore-names-textfile branch
    patch_name_file_utils_mw = mock.patch.object(name_file_utils, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        camel_wrapper, "testing_environment", True
    )

    patch_config_mw.start()
    patch_camel_wrapper_mw.start()
    patch_name_file_utils_mw.start()
    patch_testing_variable.start()

    yield

    patch_config_mw.stop()
    patch_camel_wrapper_mw.stop()
    patch_name_file_utils_mw.stop()
    patch_testing_variable.stop()


def _process(
    db_name: str,
    sentence: str,
    *,
    ignore_names_morphemizer: bool = False,
    ignore_numbers: bool = False,
    ignore_names_textfile: bool = False,
) -> list[Morpheme]:
    """Run a single sentence through the morphemizer with the given config flags.

    Skips the whole test when CAMeL Tools isn't importable so we never silently
    pass on an environment that can't actually exercise the code.
    """
    camel_wrapper.load_camel_modules()
    if not camel_wrapper.successful_import:
        pytest.skip("CAMeL Tools is not installed")

    morphemizer = CamelMorphemizer(db_name)
    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = ignore_names_morphemizer
    am_config.preprocess_ignore_numbers = ignore_numbers
    am_config.preprocess_ignore_names_textfile = ignore_names_textfile

    return next(morphemizer.get_processed_morphs(am_config, [sentence]))


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


@pytest.mark.parametrize(
    "db_name", ["calima-msa-r13", "calima-egy-r13", "calima-glf-01"]
)
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


# --- branch coverage for CamelMorphemizer.get_processed_morphs ---------------
#
# Each test below targets one branch of the processing loop, using real Arabic
# tokens whose CAMeL analysis is known to hit that branch (rather than mocking
# the analyzer, matching the approach used in spacy_test.py).


def test_camel_excluded_pos_and_source_are_skipped(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    # Punctuation (PUNC/punc), digits (DIGIT/digit) and Latin/foreign tokens
    # (FOREIGN/foreign) are filtered out via excluded_pos / excluded_sources,
    # while the real Arabic word survives.
    processed = _process("calima-msa-r13", "كتاب 5 . hello")

    inflections = [morph.inflection for morph in processed]
    assert inflections == ["كتاب"]


def test_camel_ignore_names_morphemizer_skips_proper_nouns(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    # "محمد" (Muhammad) and "القاهرة" (Cairo) are tagged noun_prop; with the
    # ignore-names option on they are dropped, leaving only the common noun.
    with_names = _process("calima-msa-r13", "محمد كتاب القاهرة")
    without_names = _process(
        "calima-msa-r13", "محمد كتاب القاهرة", ignore_names_morphemizer=True
    )

    assert "محمد" in {m.inflection for m in with_names}
    assert "القاهرة" in {m.inflection for m in with_names}
    assert [m.inflection for m in without_names] == ["كتاب"]


def test_camel_ignore_numbers_skips_noun_num(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    # In the Egyptian DB "خمسة" (five) is best-analyzed as noun_num. With the
    # ignore-numbers option on it is dropped; otherwise it is kept.
    kept = _process("calima-egy-r13", "خمسة كتاب")
    dropped = _process("calima-egy-r13", "خمسة كتاب", ignore_numbers=True)

    assert "خمسة" in {m.inflection for m in kept}
    assert "خمسة" not in {m.inflection for m in dropped}
    assert "خمسة" in {m.lemma for m in kept} or any(
        m.inflection == "خمسة" for m in kept
    )


def test_camel_ignore_names_textfile_removes_listed_words(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    # The ignore-names-textfile branch removes morphs whose inflection matches an
    # entry in the user's names file. We control that set directly here.
    with mock.patch.object(
        name_file_utils, "get_names_from_file", return_value={"محمد"}
    ):
        processed = _process("calima-msa-r13", "محمد كتاب", ignore_names_textfile=True)

    assert [m.inflection for m in processed] == ["كتاب"]


def test_camel_word_with_no_analysis_is_skipped(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    # With backoff="NONE", an out-of-vocabulary token yields no analysis and is
    # skipped (the `if not analyses: continue` branch), while real words remain.
    processed = _process("calima-msa-r13", "كتاب زقمثبخ")

    inflections = {morph.inflection for morph in processed}
    assert "كتاب" in inflections
    assert "زقمثبخ" not in inflections


def test_camel_lemma_and_pos_are_populated(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    # The normal (append) branch: a real word produces a Morpheme whose lemma
    # differs from the surface form and whose part_of_speech is set.
    processed = _process("calima-msa-r13", "الكتاب")

    assert len(processed) == 1
    morph = processed[0]
    assert morph.inflection == "الكتاب"
    assert morph.lemma == "كِتاب"
    assert morph.part_of_speech == "NOUN"
