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
from ankimorphs.highlighting.ruby_classes import (
    FuriganaRuby,
    KanaRuby,
    KanjiRuby,
    Ruby,
    TextRuby,
)
from ankimorphs.highlighting.text_highlighter import TextHighlighter
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
CASE_JAPANESE_ONE_CORRECT_FURIGANA_OUTPUT: str = (
    """（<span morph-status="unknown"><ruby>刑事<rt>けいじ</rt></ruby></span>） （<span morph-status="unknown">刑事</span>）<span morph-status="known"><ruby>珍<rt>めずら</rt></ruby>しく</span><span morph-status="unknown"><ruby>時間<rt>じかん</rt></ruby></span><span morph-status="unknown">が</span><span morph-status="known"><ruby>空<rt>あ</rt></ruby>い</span><span morph-status="known">た</span><span morph-status="unknown">ので</span>　<span morph-status="unknown">お<ruby>前<rt>まえ</rt></ruby></span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown"><ruby>顔<rt>かお</rt></ruby></span><span morph-status="unknown">を</span>　<span morph-status="unknown"><ruby>お前<rt>まえ</rt></ruby></span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown"><ruby>見<rt>み</rt></ruby></span><span morph-status="unknown">に</span><span morph-status="undefined"><ruby>様方<rt>さまかた</rt></ruby></span><span morph-status="unknown">が</span><span morph-status="unknown"><ruby>な<rt>b</rt></ruby></span> <span morph-status="undefined"><ruby>思い出<rt>おもいだ</rt></ruby>し</span><span morph-status="learning">て</span><span morph-status="learning">くれ</span>"""
)
CASE_JAPANESE_ONE_CORRECT_TEXT_OUTPUT: str = (
    """（<span morph-status="unknown"> 刑事[けいじ]</span>） （<span morph-status="unknown">刑事</span>）<span morph-status="known"> 珍[めずら]しく</span><span morph-status="unknown"> 時間[じかん]</span><span morph-status="unknown">が</span><span morph-status="known"> 空[あ]い</span><span morph-status="known">た</span><span morph-status="unknown">ので</span>　<span morph-status="unknown">お 前[まえ]</span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown"> 顔[かお]</span><span morph-status="unknown">を</span>　<span morph-status="unknown"> お前[まえ]</span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown"> 見[み]</span><span morph-status="unknown">に</span><span morph-status="undefined"> 様方[さまかた]</span><span morph-status="unknown">が</span><span morph-status="unknown"> な[b]</span> <span morph-status="undefined"> 思い出[おもいだ]し</span><span morph-status="learning">て</span><span morph-status="learning">くれ</span>"""
)
CASE_JAPANESE_ONE_CORRECT_KANJI_OUTPUT: str = (
    """（<span morph-status="unknown">刑事</span>） （<span morph-status="unknown">刑事</span>）<span morph-status="known">珍しく</span><span morph-status="unknown">時間</span><span morph-status="unknown">が</span><span morph-status="known">空い</span><span morph-status="known">た</span><span morph-status="unknown">ので</span>　<span morph-status="unknown">お前</span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown">顔</span><span morph-status="unknown">を</span>　<span morph-status="unknown">お前</span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown">見</span><span morph-status="unknown">に</span><span morph-status="undefined">様方</span><span morph-status="unknown">が</span><span morph-status="unknown">な</span> <span morph-status="undefined">思い出し</span><span morph-status="learning">て</span><span morph-status="learning">くれ</span>"""
)
CASE_JAPANESE_ONE_CORRECT_KANA_OUTPUT: str = (
    """（<span morph-status="unknown">けいじ</span>） （<span morph-status="unknown">刑事</span>）<span morph-status="known">めずらしく</span><span morph-status="unknown">じかん</span><span morph-status="unknown">が</span><span morph-status="known">あい</span><span morph-status="known">た</span><span morph-status="unknown">ので</span>　<span morph-status="unknown">おまえ</span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown">かお</span><span morph-status="unknown">を</span>　<span morph-status="unknown">まえ</span><span morph-status="unknown">たち</span><span morph-status="unknown">の</span><span morph-status="unknown">み</span><span morph-status="unknown">に</span><span morph-status="undefined">さまかた</span><span morph-status="unknown">が</span><span morph-status="unknown">b</span> <span morph-status="undefined">おもいだし</span><span morph-status="learning">て</span><span morph-status="learning">くれ</span>"""
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
CASE_JAPANESE_THREE_CORRECT_FURIGANA_OUTPUT = '<span morph-status="known"><ruby>雪<rt>ゆき</rt></ruby></span><span morph-status="learning">が</span> <span morph-status="learning">お</span><span morph-status="undefined"><ruby>留守番<rt>るすばん</rt></ruby></span> <span morph-status="undefined"><ruby>相変<rt>あいか</rt></ruby>わら</span><span morph-status="learning">ず</span>の'
CASE_JAPANESE_THREE_CORRECT_TEXT_OUTPUT = '<span morph-status="known"> 雪[ゆき]</span><span morph-status="learning">が</span> <span morph-status="learning">お</span><span morph-status="undefined"> 留守番[るすばん]</span> <span morph-status="undefined"> 相変[あいか]わら</span><span morph-status="learning">ず</span>の'
CASE_JAPANESE_THREE_CORRECT_KANJI_OUTPUT = '<span morph-status="known">雪</span><span morph-status="learning">が</span> <span morph-status="learning">お</span><span morph-status="undefined">留守番</span> <span morph-status="undefined">相変わら</span><span morph-status="learning">ず</span>の'
CASE_JAPANESE_THREE_CORRECT_KANA_OUTPUT = '<span morph-status="known">ゆき</span><span morph-status="learning">が</span> <span morph-status="learning">お</span><span morph-status="undefined">るすばん</span> <span morph-status="undefined">あいかわら</span><span morph-status="learning">ず</span>の'

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
#                                    CASE: Ruby scenario 1
##############################################################################################
# No remaining statuses or rubies
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_1_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)

CASE_RUBY_SCENARIO_1_INPUT_TEXT = "(ㆆ _ ㆆ)"
CASE_RUBY_SCENARIO_1_CORRECT_OUTPUT = "(ㆆ _ ㆆ)"
case_ruby_scenario_1_morphs: list[Morpheme] = []

##############################################################################################
#                                    CASE: Ruby scenario 2
##############################################################################################
# Only morphs remain (no more rubies)
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_2_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_2_INPUT_TEXT = "知らない..."
CASE_RUBY_SCENARIO_2_CORRECT_OUTPUT = (
    '<span morph-status="known">知ら</span><span morph-status="learning">ない</span>...'
)
case_ruby_scenario_2_morphs = [
    Morpheme(
        lemma="知る",
        inflection="知ら",
        highest_inflection_learning_interval=50,
    ),
    Morpheme(
        lemma="ない",
        inflection="ない",
        highest_inflection_learning_interval=10,
    ),
]

##############################################################################################
#                                    CASE: Ruby scenario 3
##############################################################################################
# Only rubies remain (no more morphs)
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_3_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_3_INPUT_TEXT = "37[さんじゅうなな]！"
CASE_RUBY_SCENARIO_3_CORRECT_TEXT_OUTPUT = (
    '<span morph-status="undefined"> 37[さんじゅうなな]</span>！'
)
CASE_RUBY_SCENARIO_3_CORRECT_KANJI_OUTPUT = '<span morph-status="undefined">37</span>！'
CASE_RUBY_SCENARIO_3_CORRECT_KANA_OUTPUT = (
    '<span morph-status="undefined">さんじゅうなな</span>！'
)
CASE_RUBY_SCENARIO_3_CORRECT_FURIGANA_OUTPUT = (
    '<span morph-status="undefined"><ruby>37<rt>さんじゅうなな</rt></ruby></span>！'
)
case_ruby_scenario_3_morphs: list[Morpheme] = []

##############################################################################################
#                                    CASE: Ruby scenario 4
##############################################################################################
# No overlap between status and ruby
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_4_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_4_INPUT_TEXT = "予定[よてい]です"
CASE_RUBY_SCENARIO_4_CORRECT_TEXT_OUTPUT = '<span morph-status="known"> 予定[よてい]</span><span morph-status="learning">です</span>'
CASE_RUBY_SCENARIO_4_CORRECT_KANJI_OUTPUT = (
    '<span morph-status="known">予定</span><span morph-status="learning">です</span>'
)
CASE_RUBY_SCENARIO_4_CORRECT_KANA_OUTPUT = (
    '<span morph-status="known">よてい</span><span morph-status="learning">です</span>'
)
CASE_RUBY_SCENARIO_4_CORRECT_FURIGANA_OUTPUT = '<span morph-status="known"><ruby>予定<rt>よてい</rt></ruby></span><span morph-status="learning">です</span>'
case_ruby_scenario_4_morphs = [
    Morpheme(
        lemma="予定",
        inflection="予定",
        highest_inflection_learning_interval=50,
    ),
    Morpheme(
        lemma="です",
        inflection="です",
        highest_inflection_learning_interval=10,
    ),
]

##############################################################################################
#                                    CASE: Ruby scenario 5
##############################################################################################
# Ruby and status match exactly:
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_5_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_5_INPUT_TEXT = "予定[よてい]"
CASE_RUBY_SCENARIO_5_CORRECT_TEXT_OUTPUT = (
    '<span morph-status="known"> 予定[よてい]</span>'
)
CASE_RUBY_SCENARIO_5_CORRECT_KANJI_OUTPUT = '<span morph-status="known">予定</span>'
CASE_RUBY_SCENARIO_5_CORRECT_KANA_OUTPUT = '<span morph-status="known">よてい</span>'
CASE_RUBY_SCENARIO_5_CORRECT_FURIGANA_OUTPUT = (
    '<span morph-status="known"><ruby>予定<rt>よてい</rt></ruby></span>'
)

case_ruby_scenario_5_morphs = [
    Morpheme(
        lemma="予定",
        inflection="予定",
        highest_inflection_learning_interval=50,
    ),
    Morpheme(
        lemma="です",
        inflection="です",
        highest_inflection_learning_interval=10,
    ),
]

##############################################################################################
#                                    CASE: Ruby scenario 6
##############################################################################################
# Ruby is completely inside the status:
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################

case_ruby_scenario_6_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_6_INPUT_TEXT = "相変[あいか]わらず"
CASE_RUBY_SCENARIO_6_CORRECT_TEXT_OUTPUT = (
    '<span morph-status="known"> 相変[あいか]わらず</span>'
)
CASE_RUBY_SCENARIO_6_CORRECT_KANJI_OUTPUT = (
    '<span morph-status="known">相変わらず</span>'
)
CASE_RUBY_SCENARIO_6_CORRECT_KANA_OUTPUT = (
    '<span morph-status="known">あいかわらず</span>'
)
CASE_RUBY_SCENARIO_6_CORRECT_FURIGANA_OUTPUT = (
    '<span morph-status="known"><ruby>相変<rt>あいか</rt></ruby>わらず</span>'
)
case_ruby_scenario_6_morphs = [
    Morpheme(
        lemma="相変わらず",
        inflection="相変わらず",
        highest_inflection_learning_interval=50,
    ),
]

##############################################################################################
#                                    CASE: Ruby scenario 7
##############################################################################################
# Status is completely inside the ruby
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_7_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_7_INPUT_TEXT = "錬金術師[れんきんじゅつし]"
CASE_RUBY_SCENARIO_7_CORRECT_TEXT_OUTPUT = (
    '<span morph-status="undefined"> 錬金術師[れんきんじゅつし]</span>'
)
CASE_RUBY_SCENARIO_7_CORRECT_KANJI_OUTPUT = (
    '<span morph-status="undefined">錬金術師</span>'
)
CASE_RUBY_SCENARIO_7_CORRECT_KANA_OUTPUT = (
    '<span morph-status="undefined">れんきんじゅつし</span>'
)
CASE_RUBY_SCENARIO_7_CORRECT_FURIGANA_OUTPUT = '<span morph-status="undefined"><ruby>錬金術師<rt>れんきんじゅつし</rt></ruby></span>'
case_ruby_scenario_7_morphs = [
    Morpheme(
        lemma="師",
        inflection="師",
        highest_inflection_learning_interval=50,
    ),
    Morpheme(
        lemma="錬金術",
        inflection="錬金術",
        highest_inflection_learning_interval=10,
    ),
]

##############################################################################################
#                                    CASE: Ruby scenario 8
##############################################################################################
# Status is completely inside the ruby
# Collection choice is arbitrary.
# Database choice is arbitrary.
##############################################################################################
case_ruby_scenario_8_params = FakeEnvironmentParams(
    config=config_big_japanese_collection,
)
CASE_RUBY_SCENARIO_8_INPUT_TEXT = "謎解[なぞと]き"
CASE_RUBY_SCENARIO_8_CORRECT_TEXT_OUTPUT = (
    '<span morph-status="undefined"> 謎解[なぞと]き</span>'
)
CASE_RUBY_SCENARIO_8_CORRECT_KANJI_OUTPUT = (
    '<span morph-status="undefined">謎解き</span>'
)
CASE_RUBY_SCENARIO_8_CORRECT_KANA_OUTPUT = (
    '<span morph-status="undefined">なぞとき</span>'
)
CASE_RUBY_SCENARIO_8_CORRECT_FURIGANA_OUTPUT = (
    '<span morph-status="undefined"><ruby>謎解<rt>なぞと</rt></ruby>き</span>'
)

case_ruby_scenario_8_morphs = [
    Morpheme(lemma="解き", inflection="解き", highest_inflection_learning_interval=50),
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
CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT = "私は明日[あした]"
CASE_HIGHLIGHT_UNSPACED_TEXT_OUTPUT = (
    '<span morph-status="undefined"> 私は明日[あした]</span>'
)
CASE_HIGHLIGHT_UNSPACED_KANJI_OUTPUT = '<span morph-status="undefined">私は明日</span>'
CASE_HIGHLIGHT_UNSPACED_KANA_OUTPUT = '<span morph-status="undefined">あした</span>'
CASE_HIGHLIGHT_UNSPACED_FURIGANA_OUTPUT = (
    '<span morph-status="undefined"><ruby>私は明日<rt>あした</rt></ruby></span>'
)

case_highlight_unspaced_morphs = [
    Morpheme(
        lemma="私",
        inflection="私",
        highest_inflection_learning_interval=50,
    ),
    Morpheme(
        lemma="は",
        inflection="は",
        highest_inflection_learning_interval=10,
    ),
    Morpheme(
        lemma="明日",
        inflection="明日",
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
    "fake_environment_fixture, input_text, card_morphs, correct_output, ruby_types",
    [
        (
            case_japanese_one_params,
            CASE_JAPANESE_ONE_INPUT_TEXT,
            case_japanese_one_card_morphs,
            CASE_JAPANESE_ONE_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_japanese_one_params,
            CASE_JAPANESE_ONE_INPUT_TEXT,
            case_japanese_one_card_morphs,
            CASE_JAPANESE_ONE_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_japanese_one_params,
            CASE_JAPANESE_ONE_INPUT_TEXT,
            case_japanese_one_card_morphs,
            CASE_JAPANESE_ONE_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_japanese_one_params,
            CASE_JAPANESE_ONE_INPUT_TEXT,
            case_japanese_one_card_morphs,
            CASE_JAPANESE_ONE_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_japanese_two_params,
            CASE_JAPANESE_TWO_INPUT_TEXT,
            case_japanese_two_card_morphs,
            CASE_JAPANESE_TWO_CORRECT_OUTPUT,
            [TextRuby, KanjiRuby, KanaRuby, FuriganaRuby],
        ),
        (
            case_japanese_three_params,
            CASE_JAPANESE_THREE_INPUT_TEXT,
            case_japanese_three_card_morphs,
            CASE_JAPANESE_THREE_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_japanese_three_params,
            CASE_JAPANESE_THREE_INPUT_TEXT,
            case_japanese_three_card_morphs,
            CASE_JAPANESE_THREE_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_japanese_three_params,
            CASE_JAPANESE_THREE_INPUT_TEXT,
            case_japanese_three_card_morphs,
            CASE_JAPANESE_THREE_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_japanese_three_params,
            CASE_JAPANESE_THREE_INPUT_TEXT,
            case_japanese_three_card_morphs,
            CASE_JAPANESE_THREE_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_highlight_unspaced_params,
            CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT,
            case_highlight_unspaced_morphs,
            CASE_HIGHLIGHT_UNSPACED_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_highlight_unspaced_params,
            CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT,
            case_highlight_unspaced_morphs,
            CASE_HIGHLIGHT_UNSPACED_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_highlight_unspaced_params,
            CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT,
            case_highlight_unspaced_morphs,
            CASE_HIGHLIGHT_UNSPACED_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_highlight_unspaced_params,
            CASE_HIGHLIGHT_UNSPACED_INPUT_TEXT,
            case_highlight_unspaced_morphs,
            CASE_HIGHLIGHT_UNSPACED_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_german_params,
            CASE_GERMAN_INPUT_TEXT,
            case_german_card_morphs,
            CASE_GERMAN_CORRECT_OUTPUT,
            [TextRuby, KanjiRuby, KanaRuby, FuriganaRuby],
        ),
        (
            case_regex_escape_params,
            CASE_REGEX_ESCAPE_INPUT_TEXT,
            case_regex_escape_card_morphs,
            CASE_REGEX_ESCAPE_CORRECT_OUTPUT,
            [TextRuby, KanjiRuby, KanaRuby, FuriganaRuby],
        ),
        (
            case_highlight_based_on_lemma_params,
            CASE_HIGHLIGHT_BASED_ON_LEMMA_INPUT_TEXT,
            case_highlight_based_on_lemma_morphs,
            CASE_HIGHLIGHT_BASED_ON_LEMMA_OUTPUT,
            [TextRuby, KanjiRuby, KanaRuby, FuriganaRuby],
        ),
        (
            case_ruby_scenario_1_params,
            CASE_RUBY_SCENARIO_1_INPUT_TEXT,
            case_ruby_scenario_1_morphs,
            CASE_RUBY_SCENARIO_1_CORRECT_OUTPUT,
            [TextRuby, KanjiRuby, KanaRuby, FuriganaRuby],
        ),
        (
            case_ruby_scenario_2_params,
            CASE_RUBY_SCENARIO_2_INPUT_TEXT,
            case_ruby_scenario_2_morphs,
            CASE_RUBY_SCENARIO_2_CORRECT_OUTPUT,
            [TextRuby, KanjiRuby, KanaRuby, FuriganaRuby],
        ),
        (
            case_ruby_scenario_3_params,
            CASE_RUBY_SCENARIO_3_INPUT_TEXT,
            case_ruby_scenario_3_morphs,
            CASE_RUBY_SCENARIO_3_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_ruby_scenario_3_params,
            CASE_RUBY_SCENARIO_3_INPUT_TEXT,
            case_ruby_scenario_3_morphs,
            CASE_RUBY_SCENARIO_3_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_ruby_scenario_3_params,
            CASE_RUBY_SCENARIO_3_INPUT_TEXT,
            case_ruby_scenario_3_morphs,
            CASE_RUBY_SCENARIO_3_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_ruby_scenario_3_params,
            CASE_RUBY_SCENARIO_3_INPUT_TEXT,
            case_ruby_scenario_3_morphs,
            CASE_RUBY_SCENARIO_3_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_ruby_scenario_4_params,
            CASE_RUBY_SCENARIO_4_INPUT_TEXT,
            case_ruby_scenario_4_morphs,
            CASE_RUBY_SCENARIO_4_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_ruby_scenario_4_params,
            CASE_RUBY_SCENARIO_4_INPUT_TEXT,
            case_ruby_scenario_4_morphs,
            CASE_RUBY_SCENARIO_4_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_ruby_scenario_4_params,
            CASE_RUBY_SCENARIO_4_INPUT_TEXT,
            case_ruby_scenario_4_morphs,
            CASE_RUBY_SCENARIO_4_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_ruby_scenario_4_params,
            CASE_RUBY_SCENARIO_4_INPUT_TEXT,
            case_ruby_scenario_4_morphs,
            CASE_RUBY_SCENARIO_4_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_ruby_scenario_5_params,
            CASE_RUBY_SCENARIO_5_INPUT_TEXT,
            case_ruby_scenario_5_morphs,
            CASE_RUBY_SCENARIO_5_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_ruby_scenario_5_params,
            CASE_RUBY_SCENARIO_5_INPUT_TEXT,
            case_ruby_scenario_5_morphs,
            CASE_RUBY_SCENARIO_5_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_ruby_scenario_5_params,
            CASE_RUBY_SCENARIO_5_INPUT_TEXT,
            case_ruby_scenario_5_morphs,
            CASE_RUBY_SCENARIO_5_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_ruby_scenario_5_params,
            CASE_RUBY_SCENARIO_5_INPUT_TEXT,
            case_ruby_scenario_5_morphs,
            CASE_RUBY_SCENARIO_5_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_ruby_scenario_6_params,
            CASE_RUBY_SCENARIO_6_INPUT_TEXT,
            case_ruby_scenario_6_morphs,
            CASE_RUBY_SCENARIO_6_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_ruby_scenario_6_params,
            CASE_RUBY_SCENARIO_6_INPUT_TEXT,
            case_ruby_scenario_6_morphs,
            CASE_RUBY_SCENARIO_6_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_ruby_scenario_6_params,
            CASE_RUBY_SCENARIO_6_INPUT_TEXT,
            case_ruby_scenario_6_morphs,
            CASE_RUBY_SCENARIO_6_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_ruby_scenario_6_params,
            CASE_RUBY_SCENARIO_6_INPUT_TEXT,
            case_ruby_scenario_6_morphs,
            CASE_RUBY_SCENARIO_6_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_ruby_scenario_7_params,
            CASE_RUBY_SCENARIO_7_INPUT_TEXT,
            case_ruby_scenario_7_morphs,
            CASE_RUBY_SCENARIO_7_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_ruby_scenario_7_params,
            CASE_RUBY_SCENARIO_7_INPUT_TEXT,
            case_ruby_scenario_7_morphs,
            CASE_RUBY_SCENARIO_7_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_ruby_scenario_7_params,
            CASE_RUBY_SCENARIO_7_INPUT_TEXT,
            case_ruby_scenario_7_morphs,
            CASE_RUBY_SCENARIO_7_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_ruby_scenario_7_params,
            CASE_RUBY_SCENARIO_7_INPUT_TEXT,
            case_ruby_scenario_7_morphs,
            CASE_RUBY_SCENARIO_7_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
        (
            case_ruby_scenario_8_params,
            CASE_RUBY_SCENARIO_8_INPUT_TEXT,
            case_ruby_scenario_8_morphs,
            CASE_RUBY_SCENARIO_8_CORRECT_TEXT_OUTPUT,
            [TextRuby],
        ),
        (
            case_ruby_scenario_8_params,
            CASE_RUBY_SCENARIO_8_INPUT_TEXT,
            case_ruby_scenario_8_morphs,
            CASE_RUBY_SCENARIO_8_CORRECT_KANJI_OUTPUT,
            [KanjiRuby],
        ),
        (
            case_ruby_scenario_8_params,
            CASE_RUBY_SCENARIO_8_INPUT_TEXT,
            case_ruby_scenario_8_morphs,
            CASE_RUBY_SCENARIO_8_CORRECT_KANA_OUTPUT,
            [KanaRuby],
        ),
        (
            case_ruby_scenario_8_params,
            CASE_RUBY_SCENARIO_8_INPUT_TEXT,
            case_ruby_scenario_8_morphs,
            CASE_RUBY_SCENARIO_8_CORRECT_FURIGANA_OUTPUT,
            [FuriganaRuby],
        ),
    ],
    indirect=["fake_environment_fixture"],
)
def test_highlighting(  # pylint:disable=unused-argument
    fake_environment_fixture: FakeEnvironment,
    input_text: str,
    card_morphs: list[Morpheme],
    correct_output: str,
    ruby_types: list[type[Ruby]],
) -> None:

    # needs to be cleared between runs since the learning intervals are
    # manually created and therefore inconsistent across tests
    Morpheme.get_learning_status.cache_clear()

    am_config = AnkiMorphsConfig()

    # for text without rubies it's preferable to cycle through all the
    # ruby types for extra confirmation, since they should all produce
    # the same result.
    for ruby_type in ruby_types:
        highlighted_text: str = TextHighlighter(
            am_config, input_text, card_morphs, ruby_type
        ).highlighted()
        assert highlighted_text == correct_output
