from __future__ import annotations

from test.fake_configs import (
    config_big_japanese_collection,
    config_lemma_evaluation_ignore_brackets,
)
from test.fake_environment_module import (  # pylint:disable=unused-import
    FakeEnvironment,
    FakeEnvironmentParams,
    fake_environment,
)

import pytest

from ankimorphs import text_highlighting
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme

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
case_japanese_one_params = FakeEnvironmentParams(
    collection="ignore_names_txt_collection",
    config=config_big_japanese_collection,
)

CASE_JAPANESE_ONE_INPUT_TEXT: str = (
    "珍[めずら]しく 時間[じかん]が 空[あ]いたので　お 前[まえ]たちの 顔[かお]を 見[み]に な[b]"
)
CASE_JAPANESE_ONE_CORRECT_OUTPUT: str = (
    '<span morph-status="unknown">珍[めずら]しく</span> <span morph-status="unknown">時間[じかん]</span><span morph-status="unknown">が</span> <span morph-status="unknown">空[あ]い</span><span morph-status="unknown">た</span><span morph-status="unknown">ので</span>　お 前[まえ]<span morph-status="unknown">たち</span><span morph-status="unknown">の</span> <span morph-status="unknown">顔[かお]</span><span morph-status="unknown">を</span> <span morph-status="unknown">見[み]</span><span morph-status="unknown">に</span> <span morph-status="unknown">な[b]</span>'
)
case_japanese_one_card_morphs: list[Morpheme] = [
    Morpheme(lemma="お前", inflection="お前", highest_inflection_learning_interval=0),
    Morpheme(lemma="が", inflection="が", highest_inflection_learning_interval=0),
    Morpheme(lemma="た", inflection="た", highest_inflection_learning_interval=0),
    Morpheme(lemma="たち", inflection="たち", highest_inflection_learning_interval=0),
    Morpheme(lemma="な", inflection="な", highest_inflection_learning_interval=0),
    Morpheme(lemma="に", inflection="に", highest_inflection_learning_interval=0),
    Morpheme(lemma="の", inflection="の", highest_inflection_learning_interval=0),
    Morpheme(lemma="ので", inflection="ので", highest_inflection_learning_interval=0),
    Morpheme(lemma="を", inflection="を", highest_inflection_learning_interval=0),
    Morpheme(lemma="時間", inflection="時間", highest_inflection_learning_interval=0),
    Morpheme(
        lemma="珍しい", inflection="珍しく", highest_inflection_learning_interval=0
    ),
    Morpheme(lemma="空く", inflection="空い", highest_inflection_learning_interval=0),
    Morpheme(lemma="見る", inflection="見", highest_inflection_learning_interval=0),
    Morpheme(lemma="顔", inflection="顔", highest_inflection_learning_interval=0),
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
    collection="ignore_names_txt_collection",
    config=config_big_japanese_collection,
)
CASE_JAPANESE_TWO_INPUT_TEXT = "そうです ね"
CASE_JAPANESE_TWO_CORRECT_OUTPUT = "そうです ね"
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
    collection="ignore_names_txt_collection",
    config=config_big_japanese_collection,
)
CASE_GERMAN_INPUT_TEXT = "Das sind doch die Schädel von den Flüchtlingen, die wir gefunden hatten! Keine Sorge, dein Kopf wird auch schon bald in meiner Sammlung sein."
CASE_GERMAN_CORRECT_OUTPUT = '<span morph-status="unknown">Das</span> <span morph-status="unknown">sind</span> <span morph-status="unknown">doch</span> <span morph-status="unknown">die</span> <span morph-status="unknown">Schädel</span> <span morph-status="unknown">von</span> <span morph-status="unknown">den</span> <span morph-status="unknown">Flüchtlingen</span>, <span morph-status="unknown">die</span> <span morph-status="unknown">wir</span> <span morph-status="unknown">gefunden</span> <span morph-status="unknown">hatten</span>! <span morph-status="unknown">Keine</span> <span morph-status="unknown">Sorge</span>, <span morph-status="unknown">dein</span> <span morph-status="unknown">Kopf</span> <span morph-status="unknown">wird</span> <span morph-status="unknown">auch</span> <span morph-status="unknown">schon</span> <span morph-status="unknown">bald</span> <span morph-status="unknown">in</span> <span morph-status="unknown">meiner</span> <span morph-status="unknown">Sammlung</span> <span morph-status="unknown">sein</span>.'
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
    collection="ignore_names_txt_collection",
    config=config_big_japanese_collection,
)
CASE_REGEX_ESCAPE_INPUT_TEXT = "몇...?<div><br></div><div>몇...</div>"
CASE_REGEX_ESCAPE_CORRECT_OUTPUT = '<span morph-status="unknown">몇</span>...?<div><br></div><div><span morph-status="unknown">몇</span>...</div>'
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
    collection="ignore_names_txt_collection",
    config=config_lemma_evaluation_ignore_brackets,
)
CASE_HIGHLIGHT_BASED_ON_LEMMA_INPUT_TEXT = "hello world"
CASE_HIGHLIGHT_BASED_ON_LEMMA_OUTPUT = (
    '<span morph-status="known">hello</span> <span morph-status="learning">world</span>'
)
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


# Note: the collection isn't actually used, so it is an arbitrary choice,
# but the config needs to have the option "preprocess_ignore_bracket_contents"
# activated
@pytest.mark.debug
@pytest.mark.parametrize(
    "fake_environment, input_text, card_morphs, correct_output",
    [
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
    ],
    indirect=["fake_environment"],
)
def test_highlighting(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
    input_text: str,
    card_morphs: list[Morpheme],
    correct_output: str,
) -> None:
    am_config = AnkiMorphsConfig()
    highlighted_text: str = text_highlighting.get_highlighted_text(
        am_config, card_morphs, input_text
    )
    assert highlighted_text == correct_output
