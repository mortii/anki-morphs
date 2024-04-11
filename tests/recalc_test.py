from __future__ import annotations

import pprint
from collections.abc import Sequence

import pytest

from ankimorphs import ankimorphs_globals, recalc, text_highlighting
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme

from .environment_setup_for_tests import (  # pylint:disable=unused-import
    FakeEnvironment,
    config_big_japanese_collection,
    config_ignore_names_txt_enabled,
    config_known_morphs_enabled,
    config_offset_enabled,
    fake_environment,
)

# these have to be lower than the others to prevent circular imports
from anki.cards import Card  # isort: skip  # pylint:disable=wrong-import-order
from anki.models import (  # isort: skip  # pylint:disable=wrong-import-order
    ModelManager,
    NotetypeDict,
    NotetypeId,
)
from anki.notes import Note  # isort: skip  # pylint:disable=wrong-import-order


class CardData:

    def __init__(  # pylint:disable=too-many-arguments
        self,
        due: int,
        extra_field_unknowns: str,
        extra_field_unknowns_count: str,
        extra_field_highlighted: str,
        extra_field_score: str,
        tags: list[str],
    ):
        self.due = due
        self.extra_field_unknowns = extra_field_unknowns
        self.extra_field_unknowns_count = extra_field_unknowns_count
        self.extra_field_highlighted = extra_field_highlighted
        self.extra_field_score = extra_field_score
        self.tags = tags

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, CardData)
        equal = True

        # use "if" for everything to get more feedback
        if self.due != other.due:
            print("Due mismatch!")
            equal = False

        if self.extra_field_unknowns != other.extra_field_unknowns:
            print("extra_field_unknowns mismatch!")
            equal = False

        if self.extra_field_unknowns_count != other.extra_field_unknowns_count:
            print("extra_field_unknowns_count mismatch!")
            equal = False

        if self.extra_field_highlighted != other.extra_field_highlighted:
            print("extra_field_highlighted mismatch!")
            equal = False

        if self.extra_field_score != other.extra_field_score:
            print("extra_field_score mismatch!")
            equal = False

        if self.tags != other.tags:
            print("tags mismatch!")
            equal = False

        if not equal:
            print("self:")
            pprint.pp(vars(self))
            print("other:")
            pprint.pp(vars(other))
        return equal


# "Using the indirect=True parameter when parametrizing a test allows to parametrize a test with a fixture
# receiving the values before passing them to a test"
# - https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization
# This means that we run the fixture AND the test function for each parameter.
@pytest.mark.external_morphemizers
@pytest.mark.parametrize(
    "fake_environment",
    [
        ("big-japanese-collection", config_big_japanese_collection),
        ("offset_new_cards_test_collection", config_offset_enabled),
        ("known-morphs-test-collection", config_known_morphs_enabled),
        ("ignore_names_txt_collection", config_ignore_names_txt_enabled),
    ],
    indirect=True,
)
def test_recalc(  # pylint:disable=too-many-locals
    fake_environment: FakeEnvironment,
):
    modified_collection = fake_environment.modified_collection
    original_collection = fake_environment.original_collection

    # pprint.pp(fake_environment.config)

    note_type_id_int = fake_environment.config["filters"][0]["note_type_id"]
    note_type_id: NotetypeId = NotetypeId(note_type_id_int)
    model_manager: ModelManager = ModelManager(modified_collection)
    note_type_dict: NotetypeDict | None = model_manager.get(note_type_id)
    assert note_type_dict is not None
    note_type_field_name_dict = model_manager.field_map(note_type_dict)

    extra_field_unknowns: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS
    ][0]

    extra_field_unknowns_count: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_UNKNOWNS_COUNT
    ][0]

    extra_field_highlighted: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_HIGHLIGHTED
    ][0]

    extra_field_score: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_SCORE
    ][0]

    card_due_dict: dict[int, CardData] = {}

    original_collection_cards = original_collection.find_cards("")
    card_collection_length = len(original_collection_cards)
    assert card_collection_length > 0  # sanity check

    for card_id in original_collection_cards:
        card: Card = original_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        score_field = note.fields[extra_field_score]

        card_due_dict[card_id] = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_score=score_field,
            tags=note.tags,
        )

    recalc._recalc_background_op(modified_collection)

    mock_collection_cards: Sequence[int] = modified_collection.find_cards("")
    assert len(mock_collection_cards) == card_collection_length

    for card_id in mock_collection_cards:
        print(f"card_id: {card_id}")

        card: Card = modified_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        score_field = note.fields[extra_field_score]

        original_card_data = card_due_dict[card_id]
        new_card_data = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_score=score_field,
            tags=note.tags,
        )

        assert card_id == card.id
        assert original_card_data == new_card_data


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
