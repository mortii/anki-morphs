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
    config=config_big_japanese_collection,
)

CASE_JAPANESE_ONE_INPUT_TEXT: str = (
    "（ 刑事[けいじ]） （刑事） 珍[めずら]しく 時間[じかん]が 空[あ]いたので　お 前[まえ]たちの 顔[かお]を　 お前[まえ]たちの 見[み]に 様方[さまかた]が な[b]  思い出[おもいだ]してくれ"
)
CASE_JAPANESE_ONE_CORRECT_OUTPUT: str = (
    """（<span morph-status="unknown"><ruby>刑事<rt>けいじ</rt></ruby></span>） （<span morph-status="unknown">刑事</span>）<span morph-status="known"><ruby>珍<rt>めずら</rt></ruby>しく</span><span morph-status="unknown"><ruby>時間<rt>じかん</rt></ruby></span><span morph-status="unknown">が</span><span morph-status="known"><ruby>空<rt>あ</rt></ruby>い</span><span morph-status="known">た</span><span morph-status="unknown">ので</span>　<span morph-status="unknown">お<ruby>前<rt>まえ</rt></ruby></span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown"><ruby>顔<rt>かお</rt></ruby></span><span morph-status="unknown">を</span>　<span morph-status="unknown"><ruby>お前<rt>まえ</rt></ruby></span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown"><ruby>見<rt>み</rt></ruby></span><span morph-status="unknown">に</span><ruby>様<span morph-status="learning">方</span><rt>さまかた</rt></ruby><span morph-status="unknown">が</span><span morph-status="unknown"><ruby>な<rt>b</rt></ruby></span> <ruby><span morph-status="unknown">思い</span><span morph-status="learning">出</span><rt>おもいだ</rt></ruby><span morph-status="learning">し</span><span morph-status="learning">て</span><span morph-status="learning">くれ</span>"""
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
    Morpheme(lemma="思い", inflection="思い", highest_inflection_learning_interval=0),
    Morpheme(lemma="出し", inflection="出し", highest_inflection_learning_interval=10),
    Morpheme(lemma="て", inflection="て", highest_inflection_learning_interval=10),
    Morpheme(lemma="くれ", inflection="くれ", highest_inflection_learning_interval=10),
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
CASE_JAPANESE_TWO_CORRECT_OUTPUT = "そうです ね"
case_japanese_two_card_morphs = [
    Morpheme(
        lemma="そうですね",
        inflection="そうですね",
        highest_inflection_learning_interval=0,
    ),
]

##############################################################################################
#                                CASE: Several cases that uncovered bugs in new impl
##############################################################################################
case_japanese_three_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_JAPANESE_THREE_INPUT_TEXT = "雪[ゆき]が お 留守番[るすばん]  相変[あいか]わらずの"
CASE_JAPANESE_THREE_CORRECT_OUTPUT = (
    '<span morph-status="known"><ruby>雪<rt>ゆき</rt></ruby></span><span morph-status="learning">が</span>'
    + " "
    + '<span morph-status="learning">お</span><ruby><span morph-status="known">留守</span><span morph-status="learning">番</span><rt>るすばん</rt></ruby>'
    + " "
    + '<ruby><span morph-status="learning">相</span><span morph-status="learning">変</span><rt>あいか</rt></ruby><span morph-status="learning">わら</span><span morph-status="learning">ず</span>の'
)

case_japanese_three_card_morphs = [
    Morpheme(lemma="雪", inflection="雪", highest_inflection_learning_interval=30),
    Morpheme(lemma="が", inflection="が", highest_inflection_learning_interval=10),
    Morpheme(lemma="留守", inflection="留守", highest_inflection_learning_interval=30),
    Morpheme(lemma="番", inflection="番", highest_inflection_learning_interval=10),
    Morpheme(lemma="お", inflection="お", highest_inflection_learning_interval=10),
    Morpheme(lemma="見事", inflection="見事", highest_inflection_learning_interval=30),
    Morpheme(lemma="腕", inflection="腕", highest_inflection_learning_interval=10),
    Morpheme(
        lemma="変わら", inflection="変わら", highest_inflection_learning_interval=10
    ),
    Morpheme(lemma="だ", inflection="だ", highest_inflection_learning_interval=10),
    Morpheme(lemma="だっ", inflection="だっ", highest_inflection_learning_interval=10),
    Morpheme(lemma="ああ", inflection="ああ", highest_inflection_learning_interval=10),
    Morpheme(lemma="ず", inflection="ず", highest_inflection_learning_interval=10),
    Morpheme(lemma="た", inflection="た", highest_inflection_learning_interval=10),
    Morpheme(lemma="相", inflection="相", highest_inflection_learning_interval=10),
]

##############################################################################################
#                                    CASE: Morph and ruby interaction
##############################################################################################
# This third example sets all the cases where morphs and rubies coexist.
# |-mmm---| |--mmm--| |---mmm-| |-mmm---| |-mmmmm-| |-mmmmm-| |--mmm--| |--m-m--|
# |----rrr| |--rrr--| |--rrr--| |--rrr--| |--rrr--| |--r-r--| |-rrrrr-| |-rrrrr-|
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_morph_and_ruby = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_MORPH_AND_RUBY_INPUT_TEXT = "12345  09876[def]  12345[abc]  12[abc] 34[abc]5  09876[def] 1 23[abc]45  012345[abc]  1234512345[abc]  0123[abc]45  12345777[zyzzzzz]"
CASE_MORPH_AND_RUBY_CORRECT_OUTPUT = '<span morph-status="unknown">12345</span> <ruby>09876<rt>def</rt></ruby> <span morph-status="unknown"><ruby>12345<rt>abc</rt></ruby></span> <span morph-status="unknown"><ruby>12<rt>abc</rt></ruby><ruby>34<rt>abc</rt></ruby>5</span> <ruby>09876<rt>def</rt></ruby> <span morph-status="unknown">1<ruby>23<rt>abc</rt></ruby>45</span> <ruby>0<span morph-status="unknown">12345</span><rt>abc</rt></ruby> <ruby><span morph-status="unknown">12345</span><span morph-status="unknown">12345</span><rt>abc</rt></ruby> <ruby>0<span morph-status="unknown">123</span><rt>abc</rt></ruby><span morph-status="unknown">45</span> <ruby><span morph-status="unknown">12345</span><span morph-status="unknown">777</span><rt>zyzzzzz</rt></ruby>'
CASE_MORPH_AND_TEXT_RUBY_CORRECT_OUTPUT = '<span morph-status="unknown">12345</span>  09876[def] <span morph-status="unknown"> 12345[abc]</span> <span morph-status="unknown"> 12[abc] 34[abc]5</span>  09876[def] <span morph-status="unknown">1 23[abc]45</span> <span morph-status="undefined"> 012345[abc]</span> <span morph-status="undefined"> 1234512345[abc]</span> <span morph-status="undefined"> 0123[abc]45</span> <span morph-status="undefined"> 12345777[zyzzzzz]</span>'

case_morph_and_ruby_card_morphs = [
    Morpheme(
        lemma="12345",
        inflection="12345",
        highest_inflection_learning_interval=0,
    ),
    Morpheme(
        lemma="777",
        inflection="777",
        highest_inflection_learning_interval=0,
    ),
]

##############################################################################################
#                                    CASE: Morph and ruby interaction
##############################################################################################
# Special test for codepath "7" - The ruby starts then status starts, ruby ends, status ends
# |---mmm-|
# |--rrr--|
##############################################################################################
case_morph_and_ruby_path_7 = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_MORPH_AND_RUBY_INPUT_TEXT_PATH_7 = "文書[ぶんしょ]を 謎解[なぞと]きに"
CASE_MORPH_AND_RUBY_CORRECT_OUTPUT_PATH_7 = '<span morph-status="unknown"><ruby>文書<rt>ぶんしょ</rt></ruby></span><span morph-status="known">を</span><ruby><span morph-status="unknown">謎</span><span morph-status="unknown">解</span><rt>なぞと</rt></ruby><span morph-status="unknown">き</span><span morph-status="known">に</span>'
CASE_MORPH_AND_TEXT_RUBY_CORRECT_OUTPUT_PATH_7 = '<span morph-status="unknown"> 文書[ぶんしょ]</span><span morph-status="known">を</span><span morph-status="undefined"> 謎解[なぞと]き</span><span morph-status="known">に</span>'

case_morph_and_ruby_card_morphs1 = [
    Morpheme(lemma="に", inflection="に", highest_inflection_learning_interval=100),
    Morpheme(lemma="を", inflection="を", highest_inflection_learning_interval=100),
    Morpheme(lemma="文書", inflection="文書", highest_inflection_learning_interval=0),
    Morpheme(lemma="解き", inflection="解き", highest_inflection_learning_interval=0),
    Morpheme(lemma="謎", inflection="謎", highest_inflection_learning_interval=0),
]

##############################################################################################
#                                CASE: HIGHLIGHT BASED UNSPACED TEXT
##############################################################################################
# Highlight the text the best we can without spaces to determine where to place rubies.
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_highlight_unspaced_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT = "私は明日[あした]新しい[あたらしい]。"
CASE_HIGHLIGHT_UNSPACED_OUTPUT = '<ruby><span morph-status="known">私</span>は<span morph-status="learning">明日</span><rt>あした</rt></ruby><ruby>新しい<rt>あたらしい</rt></ruby>。'
case_highlight_unspaced_morphs = [
    Morpheme(
        lemma="私",
        inflection="私",
        highest_inflection_learning_interval=30,
        highest_lemma_learning_interval=30,
    ),
    Morpheme(
        lemma="明日",
        inflection="明日",
        highest_inflection_learning_interval=10,
        highest_lemma_learning_interval=10,
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
    config=config_big_japanese_collection,
)
CASE_REGEX_ESCAPE_INPUT_TEXT = "몇...?<div><br></div><div>몇...</div> also 1 > 2, [I think that 2<1] don't forget; (sometimes I do)!"
CASE_REGEX_ESCAPE_CORRECT_OUTPUT = """<span morph-status="unknown">몇</span>...?<div><br></div><div><span morph-status="unknown">몇</span>...</div> also 1 > 2, [I think that 2<1] don't forget; (sometimes I do)!"""
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
@pytest.mark.parametrize(
    "fake_environment_fixture, input_text, card_morphs, correct_output, use_html_rubies",
    [
        (
            case_japanese_one_params,
            CASE_JAPANESE_ONE_INPUT_TEXT,
            case_japanese_one_card_morphs,
            CASE_JAPANESE_ONE_CORRECT_OUTPUT,
            True,
        ),
        (
            case_japanese_two_params,
            CASE_JAPANESE_TWO_INPUT_TEXT,
            case_japanese_two_card_morphs,
            CASE_JAPANESE_TWO_CORRECT_OUTPUT,
            True,
        ),
        (
            case_japanese_three_params,
            CASE_JAPANESE_THREE_INPUT_TEXT,
            case_japanese_three_card_morphs,
            CASE_JAPANESE_THREE_CORRECT_OUTPUT,
            True,
        ),
        (
            case_morph_and_ruby,
            CASE_MORPH_AND_RUBY_INPUT_TEXT,
            case_morph_and_ruby_card_morphs,
            CASE_MORPH_AND_RUBY_CORRECT_OUTPUT,
            True,
        ),
        (
            case_morph_and_ruby,
            CASE_MORPH_AND_RUBY_INPUT_TEXT,
            case_morph_and_ruby_card_morphs,
            CASE_MORPH_AND_TEXT_RUBY_CORRECT_OUTPUT,
            False,
        ),
        (
            case_highlight_unspaced_params,
            CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT,
            case_highlight_unspaced_morphs,
            CASE_HIGHLIGHT_UNSPACED_OUTPUT,
            True,
        ),
        (
            case_german_params,
            CASE_GERMAN_INPUT_TEXT,
            case_german_card_morphs,
            CASE_GERMAN_CORRECT_OUTPUT,
            True,
        ),
        (
            case_regex_escape_params,
            CASE_REGEX_ESCAPE_INPUT_TEXT,
            case_regex_escape_card_morphs,
            CASE_REGEX_ESCAPE_CORRECT_OUTPUT,
            True,
        ),
        (
            case_highlight_based_on_lemma_params,
            CASE_HIGHLIGHT_BASED_ON_LEMMA_INPUT_TEXT,
            case_highlight_based_on_lemma_morphs,
            CASE_HIGHLIGHT_BASED_ON_LEMMA_OUTPUT,
            True,
        ),
        (
            case_morph_and_ruby_path_7,
            CASE_MORPH_AND_RUBY_INPUT_TEXT_PATH_7,
            case_morph_and_ruby_card_morphs1,
            CASE_MORPH_AND_RUBY_CORRECT_OUTPUT_PATH_7,
            True,
        ),
        (
            case_morph_and_ruby_path_7,
            CASE_MORPH_AND_RUBY_INPUT_TEXT_PATH_7,
            case_morph_and_ruby_card_morphs1,
            CASE_MORPH_AND_TEXT_RUBY_CORRECT_OUTPUT_PATH_7,
            False,
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_highlighting(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    input_text: str,
    card_morphs: list[Morpheme],
    correct_output: str,
    use_html_rubies: bool,
) -> None:
    am_config = AnkiMorphsConfig()
    highlighted_text: str = text_highlighting.get_highlighted_text(
        am_config, card_morphs, input_text, use_html_rubies
    )
    assert highlighted_text == correct_output
