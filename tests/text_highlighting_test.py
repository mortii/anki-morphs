from __future__ import annotations

import pytest

from ankimorphs import text_highlighting
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    FakeEnvironment,
    config_big_japanese_collection,
    fake_environment,
)


# the collection isn't actually used, so it is an arbitrary choice, but the config needs to have
# the option "preprocess_ignore_bracket_contents" activated
@pytest.mark.parametrize(
    "fake_environment",
    [("ignore_names_txt_collection", config_big_japanese_collection)],
    indirect=True,
)
def test_highlighting(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
):
    # this example has a couple of good nuances:
    #   1.  空[あ]い has a ruby character in the middle of the morph
    #   2. お 前[まえ] does not match any morphs, so this checks the non-span highlighting branch
    #   3. the final [b] at the end is to make sure the final ranges work
    input_text: str = (
        "珍[めずら]しく 時間[じかん]が 空[あ]いたので　お 前[まえ]たちの 顔[かお]を 見[み]に な[b]"
    )
    correct_result: str = (
        '<span morph-status="unknown">珍[めずら]しく</span> <span morph-status="unknown">時間[じかん]</span><span morph-status="unknown">が</span> <span morph-status="unknown">空[あ]い</span><span morph-status="unknown">た</span><span morph-status="unknown">ので</span>　お 前[まえ]<span morph-status="unknown">たち</span><span morph-status="unknown">の</span> <span morph-status="unknown">顔[かお]</span><span morph-status="unknown">を</span> <span morph-status="unknown">見[み]</span><span morph-status="unknown">に</span> <span morph-status="unknown">な[b]</span>'
    )

    am_config = AnkiMorphsConfig()
    card_morphs: list[Morpheme] = [
        Morpheme(lemma="お前", inflection="お前", highest_learning_interval=0),
        Morpheme(lemma="が", inflection="が", highest_learning_interval=0),
        Morpheme(lemma="た", inflection="た", highest_learning_interval=0),
        Morpheme(lemma="たち", inflection="たち", highest_learning_interval=0),
        Morpheme(lemma="な", inflection="な", highest_learning_interval=0),
        Morpheme(lemma="に", inflection="に", highest_learning_interval=0),
        Morpheme(lemma="の", inflection="の", highest_learning_interval=0),
        Morpheme(lemma="ので", inflection="ので", highest_learning_interval=0),
        Morpheme(lemma="を", inflection="を", highest_learning_interval=0),
        Morpheme(lemma="時間", inflection="時間", highest_learning_interval=0),
        Morpheme(lemma="珍しい", inflection="珍しく", highest_learning_interval=0),
        Morpheme(lemma="空く", inflection="空い", highest_learning_interval=0),
        Morpheme(lemma="見る", inflection="見", highest_learning_interval=0),
        Morpheme(lemma="顔", inflection="顔", highest_learning_interval=0),
    ]

    highlighted_text: str = text_highlighting.get_highlighted_text(
        am_config, card_morphs, input_text
    )

    assert highlighted_text == correct_result

    # This second example the morphemizer finds the correct morph. However, the regex does
    # not match the morph because of the whitespace between 'す ね', which means that no
    # spans are made, potentially causing an 'index out of range' error immediately.
    input_text = "そうです ね"
    card_morphs = [
        Morpheme(
            lemma="そうですね", inflection="そうですね", highest_learning_interval=0
        ),
    ]
    correct_result = "そうです ね"
    highlighted_text = text_highlighting.get_highlighted_text(
        am_config, card_morphs, input_text
    )

    assert highlighted_text == correct_result

    # This third example checks if letter casing is preserved in the highlighted version
    input_text = "Das sind doch die Schädel von den Flüchtlingen, die wir gefunden hatten! Keine Sorge, dein Kopf wird auch schon bald in meiner Sammlung sein."
    card_morphs = [
        Morpheme(
            lemma="Flüchtling", inflection="flüchtlingen", highest_learning_interval=0
        ),
        Morpheme(lemma="Sammlung", inflection="sammlung", highest_learning_interval=0),
        Morpheme(lemma="finden", inflection="gefunden", highest_learning_interval=0),
        Morpheme(lemma="Schädel", inflection="schädel", highest_learning_interval=0),
        Morpheme(lemma="haben", inflection="hatten", highest_learning_interval=0),
        Morpheme(lemma="mein", inflection="meiner", highest_learning_interval=0),
        Morpheme(lemma="Sorge", inflection="sorge", highest_learning_interval=0),
        Morpheme(lemma="kein", inflection="keine", highest_learning_interval=0),
        Morpheme(lemma="schon", inflection="schon", highest_learning_interval=0),
        Morpheme(lemma="Kopf", inflection="kopf", highest_learning_interval=0),
        Morpheme(lemma="auch", inflection="auch", highest_learning_interval=0),
        Morpheme(lemma="bald", inflection="bald", highest_learning_interval=0),
        Morpheme(lemma="dein", inflection="dein", highest_learning_interval=0),
        Morpheme(lemma="doch", inflection="doch", highest_learning_interval=0),
        Morpheme(lemma="sein", inflection="sein", highest_learning_interval=0),
        Morpheme(lemma="sein", inflection="sind", highest_learning_interval=0),
        Morpheme(lemma="werden", inflection="wird", highest_learning_interval=0),
        Morpheme(lemma="der", inflection="das", highest_learning_interval=0),
        Morpheme(lemma="der", inflection="den", highest_learning_interval=0),
        Morpheme(lemma="der", inflection="die", highest_learning_interval=0),
        Morpheme(lemma="von", inflection="von", highest_learning_interval=0),
        Morpheme(lemma="wir", inflection="wir", highest_learning_interval=0),
        Morpheme(lemma="in", inflection="in", highest_learning_interval=0),
    ]
    correct_result = '<span morph-status="unknown">Das</span> <span morph-status="unknown">sind</span> <span morph-status="unknown">doch</span> <span morph-status="unknown">die</span> <span morph-status="unknown">Schädel</span> <span morph-status="unknown">von</span> <span morph-status="unknown">den</span> <span morph-status="unknown">Flüchtlingen</span>, <span morph-status="unknown">die</span> <span morph-status="unknown">wir</span> <span morph-status="unknown">gefunden</span> <span morph-status="unknown">hatten</span>! <span morph-status="unknown">Keine</span> <span morph-status="unknown">Sorge</span>, <span morph-status="unknown">dein</span> <span morph-status="unknown">Kopf</span> <span morph-status="unknown">wird</span> <span morph-status="unknown">auch</span> <span morph-status="unknown">schon</span> <span morph-status="unknown">bald</span> <span morph-status="unknown">in</span> <span morph-status="unknown">meiner</span> <span morph-status="unknown">Sammlung</span> <span morph-status="unknown">sein</span>.'
    highlighted_text = text_highlighting.get_highlighted_text(
        am_config, card_morphs, input_text
    )

    assert highlighted_text == correct_result

    # This fourth example checks if morphs with special regex characters are escaped properly
    input_text = "몇...?<div><br></div><div>몇...</div>"
    card_morphs = [
        Morpheme(lemma="?몇", inflection="?몇", highest_learning_interval=0),
        Morpheme(lemma="몇", inflection="몇", highest_learning_interval=0),
    ]
    correct_result = '<span morph-status="unknown">몇</span>...?<div><br></div><div><span morph-status="unknown">몇</span>...</div>'
    highlighted_text = text_highlighting.get_highlighted_text(
        am_config, card_morphs, input_text
    )

    assert highlighted_text == correct_result
