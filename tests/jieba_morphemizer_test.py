import os
import sys
from unittest import mock

import pytest

from ankimorphs import spacy_wrapper
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_name


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    fake_morphemizers_path = os.path.join(tests_path, "morphemizers")

    sys.path.append(fake_morphemizers_path)
    patch_testing_variable.start()
    yield
    patch_testing_variable.stop()
    sys.path.remove(fake_morphemizers_path)


@pytest.mark.external_morphemizers
def test_morpheme_generation(fake_environment):  # pylint:disable=unused-argument
    morphemizer = get_morphemizer_by_name("JiebaMorphemizer")

    # sentence = "本当に重要な任務の時しか 動かない"
    sentence = "请您说得慢些好吗？"
    correct_morphs: set[Morpheme] = {
        Morpheme("吗", "吗"),
        Morpheme("好", "好"),
        Morpheme("得", "得"),
        Morpheme("您", "您"),
        Morpheme("慢些", "慢些"),
        Morpheme("说", "说"),
        Morpheme("请", "请"),
    }

    extracted_morphs = morphemizer.get_morphemes_from_expr(sentence)
    assert len(extracted_morphs) == 7

    for morph in extracted_morphs:
        assert morph in correct_morphs
