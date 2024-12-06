from __future__ import annotations

from test.fake_configs import (
    config_big_japanese_collection,
    config_lemma_evaluation_ignore_brackets,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment_fixture,
)

import pytest

from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme
from ankimorphs.text_highlighting import get_highlighted_text

##############################################################################################
#                                    CASE: JAPANESE ONE
##############################################################################################
# This example has a couple of good nuances:
#   1.  空[あ]い has a ruby character in the middle of the morph
#   2. お 前[まえ] does not match any morphs, so this checks the non-span highlighting branch
#   3. the final [b] at the end is to make sure the final ranges work
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_japanese_one_params = FakeEnvironmentParams(config=config_big_japanese_collection)

CASE_JAPANESE_ONE_INPUT_TEXT: str = (
    "（ 刑事[けいじ]） （刑事） 珍[めずら]しく 時間[じかん]が 空[あ]いたので　お 前[まえ]たちの 顔[かお]を　 お前[まえ]たちの 見[み]に 様方[さまかた]が な[b]"
)
CASE_JAPANESE_ONE_CORRECT_OUTPUT: str = (
    """<ruby><span morph-status="unprocessed">（</span></ruby>
<ruby><span morph-status="unknown">刑事</span><rt morph-status="unknown">けいじ</rt><span morph-status="unprocessed">）</span></ruby>
<ruby><span morph-status="unprocessed">（刑事）</span></ruby>
<ruby><span morph-status="known">珍</span><rt morph-status="known">めずら</rt><span morph-status="known">しく</span></ruby>
<ruby><span morph-status="unknown">時間</span><rt morph-status="unknown">じかん</rt><span morph-status="unknown">が</span></ruby>
<ruby><span morph-status="known">空</span><rt morph-status="known">あ</rt><span morph-status="known">い</span><span morph-status="known">た</span><span morph-status="unknown">ので</span><span morph-status="unprocessed">　お</span></ruby>
<ruby><span morph-status="unprocessed">前</span><rt morph-status="unprocessed">まえ</rt><span morph-status="unknown">たち</span><span morph-status="unknown">の</span></ruby>
<ruby><span morph-status="unknown">顔</span><rt morph-status="unknown">かお</rt><span morph-status="unknown">を</span><span morph-status="unprocessed">　</span></ruby>
<ruby><span morph-status="unknown">お前</span><rt morph-status="unknown">まえ</rt><span morph-status="unknown">たち</span><span morph-status="unknown">の</span></ruby>
<ruby><span morph-status="unknown">見</span><rt morph-status="unknown">み</rt><span morph-status="unknown">に</span></ruby>
<ruby><span morph-status="unprocessed">様</span><span morph-status="learning">方</span><rt morph-status="learning">さまかた</rt><span morph-status="unknown">が</span></ruby>
<ruby><span morph-status="unknown">な</span><rt morph-status="unknown">b</rt></ruby>"""
)
case_japanese_one_card_morphs: list[Morpheme] = [
    Morpheme(lemma="刑事", inflection="刑事", highest_inflection_learning_interval=0),
    Morpheme(lemma="お前", inflection="お前", highest_inflection_learning_interval=0),
    Morpheme(lemma="が", inflection="が", highest_inflection_learning_interval=0),
    Morpheme(lemma="た", inflection="た", highest_inflection_learning_interval=30),
    Morpheme(lemma="たち", inflection="たち", highest_inflection_learning_interval=0),
    Morpheme(lemma="な", inflection="な", highest_inflection_learning_interval=0),
    Morpheme(lemma="に", inflection="に", highest_inflection_learning_interval=0),
    Morpheme(lemma="の", inflection="の", highest_inflection_learning_interval=0),
    Morpheme(lemma="ので", inflection="ので", highest_inflection_learning_interval=0),
    Morpheme(lemma="を", inflection="を", highest_inflection_learning_interval=0),
    Morpheme(lemma="時間", inflection="時間", highest_inflection_learning_interval=0),
    Morpheme(
        lemma="珍しい", inflection="珍しく", highest_inflection_learning_interval=30
    ),
    Morpheme(lemma="空く", inflection="空い", highest_inflection_learning_interval=30),
    Morpheme(lemma="見る", inflection="見", highest_inflection_learning_interval=0),
    Morpheme(lemma="顔", inflection="顔", highest_inflection_learning_interval=0),
    Morpheme(lemma="方", inflection="方", highest_inflection_learning_interval=1),
]


##############################################################################################
#                                    CASE: JAPANESE TWO
##############################################################################################
# This second example the morphemizer finds the correct morph. However, the regex does
# not match the morph because of the whitespace between 'す ね', which means that no
# spans are made, potentially causing an 'index out of range' error immediately.
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_japanese_two_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_JAPANESE_TWO_INPUT_TEXT = "そうです ね"
CASE_JAPANESE_TWO_CORRECT_OUTPUT = """<ruby><span morph-status="unprocessed">そうです</span></ruby>
<ruby><span morph-status="unprocessed">ね</span></ruby>"""
case_japanese_two_card_morphs = [
    Morpheme(
        lemma="そうですね",
        inflection="そうですね",
        highest_inflection_learning_interval=0,
    ),
]


##############################################################################################
#                                         CASE: GERMAN
##############################################################################################
# This checks if letter casing is preserved in the highlighted version.
# Collection choice is arbitrary.
# Database choice is arbitrary.
# The config is arbitrary except that it needs "preprocess_ignore_bracket_contents" activated.
##############################################################################################
case_german_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_GERMAN_INPUT_TEXT = "Das sind doch die Schädel von den Flüchtlingen, die wir gefunden hatten! Keine Sorge, dein Kopf wird auch schon bald in meiner Sammlung sein."
CASE_GERMAN_CORRECT_OUTPUT = """<ruby><span morph-status="unknown">Das</span></ruby>
<ruby><span morph-status="unknown">sind</span></ruby>
<ruby><span morph-status="unknown">doch</span></ruby>
<ruby><span morph-status="unknown">die</span></ruby>
<ruby><span morph-status="unknown">Schädel</span></ruby>
<ruby><span morph-status="unknown">von</span></ruby>
<ruby><span morph-status="unknown">den</span></ruby>
<ruby><span morph-status="unknown">Flüchtlingen</span><span morph-status="unprocessed">,</span></ruby>
<ruby><span morph-status="unknown">die</span></ruby>
<ruby><span morph-status="unknown">wir</span></ruby>
<ruby><span morph-status="unknown">gefunden</span></ruby>
<ruby><span morph-status="unknown">hatten</span><span morph-status="unprocessed">!</span></ruby>
<ruby><span morph-status="unknown">Keine</span></ruby>
<ruby><span morph-status="unknown">Sorge</span><span morph-status="unprocessed">,</span></ruby>
<ruby><span morph-status="unknown">dein</span></ruby>
<ruby><span morph-status="unknown">Kopf</span></ruby>
<ruby><span morph-status="unknown">wird</span></ruby>
<ruby><span morph-status="unknown">auch</span></ruby>
<ruby><span morph-status="unknown">schon</span></ruby>
<ruby><span morph-status="unknown">bald</span></ruby>
<ruby><span morph-status="unknown">in</span></ruby>
<ruby><span morph-status="unknown">meiner</span></ruby>
<ruby><span morph-status="unknown">Sammlung</span></ruby>
<ruby><span morph-status="unknown">sein</span><span morph-status="unprocessed">.</span></ruby>"""
case_german_card_morphs = [
    Morpheme(
        lemma="Flüchtling",
        inflection="flüchtlingen",
        highest_inflection_learning_interval=0,
    ),
    Morpheme(
        lemma="Sammlung",
        inflection="sammlung",
        highest_inflection_learning_interval=0,
    ),
    Morpheme(
        lemma="finden",
        inflection="gefunden",
        highest_inflection_learning_interval=0,
    ),
    Morpheme(
        lemma="Schädel",
        inflection="schädel",
        highest_inflection_learning_interval=0,
    ),
    Morpheme(
        lemma="haben", inflection="hatten", highest_inflection_learning_interval=0
    ),
    Morpheme(lemma="mein", inflection="meiner", highest_inflection_learning_interval=0),
    Morpheme(lemma="Sorge", inflection="sorge", highest_inflection_learning_interval=0),
    Morpheme(lemma="kein", inflection="keine", highest_inflection_learning_interval=0),
    Morpheme(lemma="schon", inflection="schon", highest_inflection_learning_interval=0),
    Morpheme(lemma="Kopf", inflection="kopf", highest_inflection_learning_interval=0),
    Morpheme(lemma="auch", inflection="auch", highest_inflection_learning_interval=0),
    Morpheme(lemma="bald", inflection="bald", highest_inflection_learning_interval=0),
    Morpheme(lemma="dein", inflection="dein", highest_inflection_learning_interval=0),
    Morpheme(lemma="doch", inflection="doch", highest_inflection_learning_interval=0),
    Morpheme(lemma="sein", inflection="sein", highest_inflection_learning_interval=0),
    Morpheme(lemma="sein", inflection="sind", highest_inflection_learning_interval=0),
    Morpheme(lemma="werden", inflection="wird", highest_inflection_learning_interval=0),
    Morpheme(lemma="der", inflection="das", highest_inflection_learning_interval=0),
    Morpheme(lemma="der", inflection="den", highest_inflection_learning_interval=0),
    Morpheme(lemma="der", inflection="die", highest_inflection_learning_interval=0),
    Morpheme(lemma="von", inflection="von", highest_inflection_learning_interval=0),
    Morpheme(lemma="wir", inflection="wir", highest_inflection_learning_interval=0),
    Morpheme(lemma="in", inflection="in", highest_inflection_learning_interval=0),
]

##############################################################################################
#                                         CASE: REGEX_ESCAPE
##############################################################################################
# This fourth example checks if morphs with special regex characters are escaped properly
# Collection choice is arbitrary.
# Database choice is arbitrary.
# The config is arbitrary except that it needs "preprocess_ignore_bracket_contents" activated.
##############################################################################################
case_regex_escape_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_REGEX_ESCAPE_INPUT_TEXT = "몇...?<div><br></div><div>몇...</div> also 1 > 2, [I think that 2<1] don't forget; (sometimes I do)!"
CASE_REGEX_ESCAPE_CORRECT_OUTPUT = """<ruby><span morph-status="unknown">몇</span><span morph-status="unprocessed">...?</span></ruby><div><br></div><div><ruby><span morph-status="unknown">몇</span><span morph-status="unprocessed">...</span></ruby></div>
<ruby><span morph-status="unprocessed">also</span></ruby>
<ruby><span morph-status="unprocessed">1</span></ruby>
<ruby><span morph-status="unprocessed">></span></ruby>
<ruby><span morph-status="unprocessed">2,</span></ruby>
<ruby><span morph-status="unprocessed">[I</span></ruby>
<ruby><span morph-status="unprocessed">think</span></ruby>
<ruby><span morph-status="unprocessed">that</span></ruby>
<ruby><span morph-status="unprocessed">2</span></ruby><<ruby><span morph-status="unprocessed">1]</span></ruby>
<ruby><span morph-status="unprocessed">don't</span></ruby>
<ruby><span morph-status="unprocessed">forget;</span></ruby>
<ruby><span morph-status="unprocessed">(sometimes</span></ruby>
<ruby><span morph-status="unprocessed">I</span></ruby>
<ruby><span morph-status="unprocessed">do)!</span></ruby>"""
case_regex_escape_card_morphs = [
    Morpheme(lemma="?몇", inflection="?몇", highest_inflection_learning_interval=0),
    Morpheme(lemma="몇", inflection="몇", highest_inflection_learning_interval=0),
]

##############################################################################################
#                                CASE: HIGHLIGHT BASED ON LEMMA
##############################################################################################
# Highlight the inflections based on the learning intervals of their respective lemmas
# Collection choice is arbitrary.
# Database choice is arbitrary.
# The config needs "preprocess_ignore_bracket_contents" activated, and "evaluate_morph_lemma".
##############################################################################################
case_highlight_based_on_lemma_params = FakeEnvironmentParams(
    config=config_lemma_evaluation_ignore_brackets,
)
CASE_HIGHLIGHT_BASED_ON_LEMMA_INPUT_TEXT = "hello world"
CASE_HIGHLIGHT_BASED_ON_LEMMA_OUTPUT = """<ruby><span morph-status="known">hello</span></ruby>
<ruby><span morph-status="learning">world</span></ruby>"""
case_highlight_based_on_lemma_morphs = [
    Morpheme(
        lemma="hello",
        inflection="hello",
        highest_inflection_learning_interval=0,
        highest_lemma_learning_interval=30,
    ),
    Morpheme(
        lemma="world",
        inflection="world",
        highest_inflection_learning_interval=0,
        highest_lemma_learning_interval=10,
    ),
]


one_test_set = [
    (
        case_japanese_one_params,
        CASE_JAPANESE_ONE_INPUT_TEXT,
        case_japanese_one_card_morphs,
        CASE_JAPANESE_ONE_CORRECT_OUTPUT,
    ),
    (
        case_japanese_two_params,
        CASE_JAPANESE_TWO_INPUT_TEXT,
        case_japanese_two_card_morphs,
        CASE_JAPANESE_TWO_CORRECT_OUTPUT,
    ),
    (
        case_german_params,
        CASE_GERMAN_INPUT_TEXT,
        case_german_card_morphs,
        CASE_GERMAN_CORRECT_OUTPUT,
    ),
    (
        case_regex_escape_params,
        CASE_REGEX_ESCAPE_INPUT_TEXT,
        case_regex_escape_card_morphs,
        CASE_REGEX_ESCAPE_CORRECT_OUTPUT,
    ),
    (
        case_highlight_based_on_lemma_params,
        CASE_HIGHLIGHT_BASED_ON_LEMMA_INPUT_TEXT,
        case_highlight_based_on_lemma_morphs,
        CASE_HIGHLIGHT_BASED_ON_LEMMA_OUTPUT,
    ),
]


# Note: the collection isn't actually used, so it is an arbitrary choice,
# but the config needs to have the option "preprocess_ignore_bracket_contents"
# activated
@pytest.mark.parametrize(
    "fake_environment_fixture, input_text, card_morphs, correct_output",
    one_test_set * 1,
    indirect=["fake_environment_fixture"],
)
def test_highlight_text_jit(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    input_text: str,
    card_morphs: list[Morpheme],
    correct_output: str,
) -> None:
    am_config = AnkiMorphsConfig()
    highlighted_text: str = get_highlighted_text(am_config, card_morphs, input_text)
    assert highlighted_text == correct_output
