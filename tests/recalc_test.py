import json
import os
import shutil
import sys
from collections.abc import Sequence
from typing import Optional
from unittest import mock

import aqt
import pytest
from anki.cards import Card
from anki.collection import Collection
from anki.models import ModelManager, NotetypeDict, NotetypeId
from anki.notes import Note
from aqt import setupLangAndBackend

from ankimorphs import (
    AnkiMorphsConfig,
    AnkiMorphsDB,
    anki_data_utils,
    ankimorphs_config,
    ankimorphs_db,
    ankimorphs_globals,
    name_file_utils,
    recalc,
    spacy_wrapper,
    text_highlighting,
)
from ankimorphs.morpheme import Morpheme


class CardData:
    __slots__ = (
        "due",
        "extra_field_unknowns",
        "extra_field_unknowns_count",
        "extra_field_highlighted",
        "extra_field_difficulty",
        "tags",
    )

    def __init__(  # pylint:disable=too-many-arguments
        self,
        due: int,
        extra_field_unknowns: str,
        extra_field_unknowns_count: str,
        extra_field_highlighted: str,
        extra_field_difficulty: str,
        tags: list[str],
    ):
        self.due = due
        self.extra_field_unknowns = extra_field_unknowns
        self.extra_field_unknowns_count = extra_field_unknowns_count
        self.extra_field_highlighted = extra_field_highlighted
        self.extra_field_difficulty = extra_field_difficulty
        self.tags = tags

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, CardData)
        return all(
            [
                self.due == other.due,
                self.extra_field_unknowns == other.extra_field_unknowns,
                self.extra_field_unknowns_count == other.extra_field_unknowns_count,
                self.extra_field_highlighted == other.extra_field_highlighted,
                self.extra_field_difficulty == other.extra_field_difficulty,
                self.tags == other.tags,
            ]
        )


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment_no_offset():
    # deck used is found here: https://github.com/mortii/anki-decks
    # "Japanese Sentences_v5.apkg"
    # the collection.ank2 file only stores the collection data, not media.

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    collection_path_original = os.path.join(tests_path, "collection.anki2")
    collection_path_duplicate = os.path.join(tests_path, "duplicate_collection.anki2")
    collection_path_duplicate_media = os.path.join(
        tests_path, "duplicate_collection.media"
    )
    fake_morphemizers_path = os.path.join(tests_path, "morphemizers")

    # print(f"current dir: {os.getcwd()}")

    _config_data = None
    with open(os.path.join(tests_path, "meta.json"), encoding="utf-8") as file:
        _config_data = json.load(file)

    # If the destination already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.pm.profileFolder.return_value = os.path.join("tests", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data["config"]

    patch_recalc_mw = mock.patch.object(recalc, "mw", mock_mw)
    morph_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_name_file_utils_mw = mock.patch.object(name_file_utils, "mw", mock_mw)
    patch_anki_data_utils_mw = mock.patch.object(anki_data_utils, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    patch_recalc_mw.start()
    morph_db_mw.start()
    patch_config_mw.start()
    patch_name_file_utils_mw.start()
    patch_anki_data_utils_mw.start()
    patch_testing_variable.start()
    sys.path.append(fake_morphemizers_path)

    yield mock_mw.col, Collection(collection_path_original)

    mock_mw.col.close()

    patch_recalc_mw.stop()
    morph_db_mw.stop()
    patch_config_mw.stop()
    patch_name_file_utils_mw.stop()
    patch_anki_data_utils_mw.stop()
    patch_testing_variable.stop()

    os.remove(collection_path_duplicate)
    shutil.rmtree(collection_path_duplicate_media)
    sys.path.remove(fake_morphemizers_path)


@pytest.fixture()
def fake_environment_with_offset():
    # almost identical to the other fake environment, but the collection
    # has used the offset settings instead of skip

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    collection_path_original = os.path.join(tests_path, "collection_with_offset.anki2")
    collection_path_duplicate = os.path.join(
        tests_path, "duplicate_collection_with_offset.anki2"
    )
    collection_path_duplicate_media = os.path.join(
        tests_path, "duplicate_collection_with_offset.media"
    )
    fake_morphemizers_path = os.path.join(tests_path, "morphemizers")

    # print(f"current dir: {os.getcwd()}")

    _config_data = None
    with open(os.path.join(tests_path, "meta.json"), encoding="utf-8") as file:
        _config_data = json.load(file)
        _config_data["config"]["recalc_offset_new_cards"] = True
        _config_data["config"]["skip_only_known_morphs_cards"] = False
        _config_data["config"]["skip_unknown_morph_seen_today_cards"] = False

    # If the destination already exists, it will be replaced
    shutil.copyfile(collection_path_original, collection_path_duplicate)

    mock_mw = mock.Mock(spec=aqt.mw)
    mock_mw.col = Collection(collection_path_duplicate)
    mock_mw.backend = setupLangAndBackend(
        pm=mock.Mock(name="fake_pm"), app=mock.Mock(name="fake_app"), force="en"
    )
    mock_mw.pm.profileFolder.return_value = os.path.join("tests", "data")
    mock_mw.progress.want_cancel.return_value = False
    mock_mw.addonManager.getConfig.return_value = _config_data["config"]

    patch_recalc_mw = mock.patch.object(recalc, "mw", mock_mw)
    morph_db_mw = mock.patch.object(ankimorphs_db, "mw", mock_mw)
    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_name_file_utils_mw = mock.patch.object(name_file_utils, "mw", mock_mw)
    patch_anki_data_utils_mw = mock.patch.object(anki_data_utils, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    patch_recalc_mw.start()
    morph_db_mw.start()
    patch_config_mw.start()
    patch_name_file_utils_mw.start()
    patch_anki_data_utils_mw.start()
    patch_testing_variable.start()
    sys.path.append(fake_morphemizers_path)

    yield mock_mw.col, Collection(collection_path_original)

    mock_mw.col.close()

    patch_recalc_mw.stop()
    morph_db_mw.stop()
    patch_config_mw.stop()
    patch_name_file_utils_mw.stop()
    patch_anki_data_utils_mw.stop()
    patch_testing_variable.stop()

    os.remove(collection_path_duplicate)
    shutil.rmtree(collection_path_duplicate_media)
    sys.path.remove(fake_morphemizers_path)


@pytest.mark.external_morphemizers
def test_recalc_no_offset(fake_environment_no_offset):  # pylint:disable=too-many-locals
    mock_collection, original_collection = fake_environment_no_offset

    note_type_id: NotetypeId = NotetypeId(
        1691076536776  # found in tests/data/meta.json
    )
    model_manager: ModelManager = ModelManager(mock_collection)
    note_type_dict: Optional[NotetypeDict] = model_manager.get(note_type_id)
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

    extra_field_difficulty: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_DIFFICULTY
    ][0]

    card_due_dict: dict[int, CardData] = {}

    original_collection_cards = original_collection.find_cards("")
    card_collection_length = 36850
    assert len(original_collection_cards) == card_collection_length

    for card_id in original_collection_cards:
        card: Card = original_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        difficulty_field = note.fields[extra_field_difficulty]

        card_due_dict[card_id] = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_difficulty=difficulty_field,
            tags=note.tags,
        )

    recalc._recalc_background_op(mock_collection)

    mock_collection_cards: Sequence[int] = mock_collection.find_cards("")
    assert len(mock_collection_cards) == card_collection_length

    for card_id in mock_collection_cards:
        card: Card = mock_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        difficulty_field = note.fields[extra_field_difficulty]

        new_card_data = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_difficulty=difficulty_field,
            tags=note.tags,
        )

        original_card_data = card_due_dict[card_id]

        # print("original card data")
        # print(f"card_id: {card_id}")
        # print(f"due: {original_card_data.due}")
        # print(f"extra_field_unknowns: {original_card_data.extra_field_unknowns}")
        # print(
        #     f"extra_field_unknowns_count: {original_card_data.extra_field_unknowns_count}"
        # )
        # print(f"extra_field_highlighted: {original_card_data.extra_field_highlighted}")
        # print(f"extra_field_difficulty: {original_card_data.extra_field_difficulty}")
        # print(f"tags: {original_card_data.tags}")

        assert card_id == card.id
        assert original_card_data.due == new_card_data.due
        assert (
            original_card_data.extra_field_unknowns
            == new_card_data.extra_field_unknowns
        )
        assert (
            original_card_data.extra_field_unknowns_count
            == new_card_data.extra_field_unknowns_count
        )
        assert (
            original_card_data.extra_field_highlighted
            == new_card_data.extra_field_highlighted
        )
        assert (
            original_card_data.extra_field_difficulty
            == new_card_data.extra_field_difficulty
        )
        assert original_card_data.tags == new_card_data.tags

    # we check if the morphs from 'known-morphs' dir is correctly inserted into the db
    known_morphs_test: list[tuple[str, str]] = AnkiMorphsDB.get_known_morphs(
        highest_learning_interval=21
    )
    known_morphs_correct = [("æ", "æ"), ("ø", "ø")]

    assert known_morphs_test == known_morphs_correct


def test_highlighting(fake_environment_no_offset):  # pylint:disable=unused-argument
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


@pytest.mark.xfail
def test_names_txt_file():
    # there isn't really a great way to test name.txt since removing
    # morphs will cause a cascade of due changes...
    assert False


@pytest.mark.external_morphemizers
def test_recalc_with_offset(
    fake_environment_with_offset,
):  # pylint:disable=too-many-locals
    # Identical to the other recalc test function, but with these configs on the test collection instead:
    # _config_data["config"]["recalc_offset_new_cards"] = True
    # _config_data["config"]["skip_only_known_morphs_cards"] = False
    # _config_data["config"]["skip_unknown_morph_seen_today_cards"] = False

    mock_collection, original_collection = fake_environment_with_offset

    note_type_id: NotetypeId = NotetypeId(
        1691076536776  # found in tests/data/meta.json
    )
    model_manager: ModelManager = ModelManager(mock_collection)
    note_type_dict: Optional[NotetypeDict] = model_manager.get(note_type_id)
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

    extra_field_difficulty: int = note_type_field_name_dict[
        ankimorphs_globals.EXTRA_FIELD_DIFFICULTY
    ][0]

    card_due_dict: dict[int, CardData] = {}

    original_collection_cards = original_collection.find_cards("")
    card_collection_length = 36850
    assert len(original_collection_cards) == card_collection_length

    for card_id in original_collection_cards:
        card: Card = original_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        difficulty_field = note.fields[extra_field_difficulty]

        card_due_dict[card_id] = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_difficulty=difficulty_field,
            tags=note.tags,
        )

    recalc._recalc_background_op(mock_collection)

    mock_collection_cards: Sequence[int] = mock_collection.find_cards("")
    assert len(mock_collection_cards) == card_collection_length

    for card_id in mock_collection_cards:
        card: Card = mock_collection.get_card(card_id)
        note: Note = card.note()

        unknowns_field = note.fields[extra_field_unknowns]
        unknowns_count_field = note.fields[extra_field_unknowns_count]
        highlighted_field = note.fields[extra_field_highlighted]
        difficulty_field = note.fields[extra_field_difficulty]

        new_card_data = CardData(
            due=card.due,
            extra_field_unknowns=unknowns_field,
            extra_field_unknowns_count=unknowns_count_field,
            extra_field_highlighted=highlighted_field,
            extra_field_difficulty=difficulty_field,
            tags=note.tags,
        )

        original_card_data = card_due_dict[card_id]

        # print("original card data")
        # print(f"card_id: {card_id}")
        # print(f"due: {original_card_data.due}")
        # print(f"extra_field_unknowns: {original_card_data.extra_field_unknowns}")
        # print(
        #     f"extra_field_unknowns_count: {original_card_data.extra_field_unknowns_count}"
        # )
        # print(f"extra_field_highlighted: {original_card_data.extra_field_highlighted}")
        # print(f"extra_field_difficulty: {original_card_data.extra_field_difficulty}")
        # print(f"tags: {original_card_data.tags}")

        assert card_id == card.id
        assert original_card_data.due == new_card_data.due
        assert (
            original_card_data.extra_field_unknowns
            == new_card_data.extra_field_unknowns
        )
        assert (
            original_card_data.extra_field_unknowns_count
            == new_card_data.extra_field_unknowns_count
        )
        assert (
            original_card_data.extra_field_highlighted
            == new_card_data.extra_field_highlighted
        )
        assert (
            original_card_data.extra_field_difficulty
            == new_card_data.extra_field_difficulty
        )
        assert original_card_data.tags == new_card_data.tags

    # we check if the morphs from 'known-morphs' dir is correctly inserted into the db
    known_morphs_test: list[tuple[str, str]] = AnkiMorphsDB.get_known_morphs(
        highest_learning_interval=21
    )
    known_morphs_correct = [("æ", "æ"), ("ø", "ø")]

    assert known_morphs_test == known_morphs_correct
