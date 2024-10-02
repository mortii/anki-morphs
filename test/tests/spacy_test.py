import json
from collections.abc import Iterator
from typing import Any
from unittest import mock

import aqt
import pytest

from ankimorphs import ankimorphs_config
from ankimorphs.ankimorphs_config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizers import spacy_wrapper
from ankimorphs.morphemizers.spacy_wrapper import get_nlp
from ankimorphs.text_preprocessing import get_processed_spacy_morphs


class SpacyMorph:
    def __init__(self, lemma: str, inflection: str, part_of_speech: str) -> None:
        self.lemma = lemma
        self.inflection = inflection
        self.part_of_speech = part_of_speech


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment_fixture() -> Iterator[None]:
    print("fake environment initiated")
    mock_mw = mock.Mock(spec=aqt.mw)  # can use any mw to spec

    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.addonManager.getConfig.return_value = _config_data
    patch_config_mw = mock.patch.object(ankimorphs_config, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    patch_config_mw.start()
    patch_testing_variable.start()
    yield
    patch_config_mw.stop()
    patch_testing_variable.stop()


@pytest.mark.parametrize(
    "spacy_model_name, sentence, expected_spacy_morphs, expected_am_morphs",
    [
        (
            "ja_core_news_sm",  # Japanese
            "半田さん　朝代わってよ",
            [
                SpacyMorph(lemma="半田", inflection="半田", part_of_speech="PROPN"),
                SpacyMorph(lemma="さん", inflection="さん", part_of_speech="NOUN"),
                SpacyMorph(lemma="　", inflection="　", part_of_speech="X"),
                SpacyMorph(lemma="朝", inflection="朝", part_of_speech="NOUN"),
                SpacyMorph(lemma="代わる", inflection="代わっ", part_of_speech="VERB"),
                SpacyMorph(lemma="て", inflection="て", part_of_speech="SCONJ"),
                SpacyMorph(lemma="よ", inflection="よ", part_of_speech="PART"),
            ],
            [
                Morpheme(lemma="さん", inflection="さん"),
                Morpheme(lemma="朝", inflection="朝"),
                Morpheme(lemma="代わる", inflection="代わっ"),
                Morpheme(lemma="て", inflection="て"),
                Morpheme(lemma="よ", inflection="よ"),
            ],
        ),
        (
            "nb_core_news_sm",  # Norwegian bokmål
            "Gikk Harald nå?",
            [
                SpacyMorph(lemma="gå", inflection="gikk", part_of_speech="VERB"),
                SpacyMorph(lemma="harald", inflection="harald", part_of_speech="PROPN"),
                SpacyMorph(lemma="nå", inflection="nå", part_of_speech="ADV"),
                SpacyMorph(lemma="$?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="gå", inflection="gikk"),
                Morpheme(lemma="nå", inflection="nå"),
            ],
        ),
        (
            "en_core_web_sm",  # English
            "At 3 o'clock, Harry's mother-in-law walked away.",
            [
                SpacyMorph(lemma="at", inflection="at", part_of_speech="ADP"),
                SpacyMorph(lemma="3", inflection="3", part_of_speech="NUM"),
                SpacyMorph(
                    lemma="o'clock", inflection="o'clock", part_of_speech="NOUN"
                ),
                SpacyMorph(lemma=",", inflection=",", part_of_speech="PUNCT"),
                SpacyMorph(lemma="harry", inflection="harry", part_of_speech="PROPN"),
                SpacyMorph(lemma="'s", inflection="'s", part_of_speech="PART"),
                SpacyMorph(
                    lemma="mother-in-law",
                    inflection="mother-in-law",
                    part_of_speech="NOUN",
                ),
                SpacyMorph(lemma="walk", inflection="walked", part_of_speech="VERB"),
                SpacyMorph(lemma="away", inflection="away", part_of_speech="ADV"),
                SpacyMorph(lemma=".", inflection=".", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="at", inflection="at"),
                Morpheme(lemma="3", inflection="3"),
                Morpheme(lemma="o'clock", inflection="o'clock"),
                Morpheme(lemma="'s", inflection="'s"),
                Morpheme(lemma="mother-in-law", inflection="mother-in-law"),
                Morpheme(lemma="walk", inflection="walked"),
                Morpheme(lemma="away", inflection="away"),
            ],
        ),
        (
            "de_core_news_md",  # German, sm model is not great
            "»Was ist los?«Harry schüttelte den Kopf und spähte.",
            [
                SpacyMorph(lemma="--", inflection="»", part_of_speech="PUNCT"),
                SpacyMorph(lemma="was", inflection="was", part_of_speech="PRON"),
                SpacyMorph(lemma="sein", inflection="ist", part_of_speech="AUX"),
                SpacyMorph(lemma="los", inflection="los", part_of_speech="ADV"),
                SpacyMorph(lemma="--", inflection="?", part_of_speech="PUNCT"),
                SpacyMorph(lemma="--", inflection="«", part_of_speech="PUNCT"),
                SpacyMorph(lemma="Harry", inflection="harry", part_of_speech="PROPN"),
                SpacyMorph(
                    lemma="schütteln", inflection="schüttelte", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="der", inflection="den", part_of_speech="DET"),
                SpacyMorph(lemma="Kopf", inflection="kopf", part_of_speech="NOUN"),
                SpacyMorph(lemma="und", inflection="und", part_of_speech="CCONJ"),
                SpacyMorph(lemma="spähen", inflection="spähte", part_of_speech="VERB"),
                SpacyMorph(lemma="--", inflection=".", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="was", inflection="was"),
                Morpheme(lemma="sein", inflection="ist"),
                Morpheme(lemma="los", inflection="los"),
                Morpheme(lemma="schütteln", inflection="schüttelte"),
                Morpheme(lemma="der", inflection="den"),
                Morpheme(lemma="Kopf", inflection="kopf"),
                Morpheme(lemma="und", inflection="und"),
                Morpheme(lemma="spähen", inflection="spähte"),
            ],
        ),
        (
            "ca_core_news_sm",  # Catalan
            "va caminar en Guillem?",
            [
                SpacyMorph(lemma="anar", inflection="va", part_of_speech="AUX"),
                SpacyMorph(
                    lemma="caminar", inflection="caminar", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="en", inflection="en", part_of_speech="ADP"),
                SpacyMorph(
                    lemma="guillem", inflection="guillem", part_of_speech="NOUN"
                ),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="anar", inflection="va"),
                Morpheme(lemma="caminar", inflection="caminar"),
                Morpheme(lemma="en", inflection="en"),
                Morpheme(lemma="guillem", inflection="guillem"),
            ],
        ),
        (
            "es_core_news_sm",  # Spanish
            "¿Pedro ya comió?",
            [
                SpacyMorph(lemma="¿", inflection="¿", part_of_speech="PUNCT"),
                SpacyMorph(lemma="pedro", inflection="pedro", part_of_speech="PROPN"),
                SpacyMorph(lemma="ya", inflection="ya", part_of_speech="ADV"),
                SpacyMorph(lemma="comer", inflection="comió", part_of_speech="VERB"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="ya", inflection="ya"),
                Morpheme(lemma="comer", inflection="comió"),
            ],
        ),
        (
            "fr_core_news_sm",  # French
            "Ça m’est égal?",
            [
                SpacyMorph(lemma="cela", inflection="ça", part_of_speech="PRON"),
                SpacyMorph(lemma="m’est", inflection="m’est", part_of_speech="VERB"),
                SpacyMorph(lemma="égal", inflection="égal", part_of_speech="ADJ"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="cela", inflection="ça"),
                Morpheme(lemma="m’est", inflection="m’est"),
                Morpheme(lemma="égal", inflection="égal"),
            ],
        ),
        (
            "da_core_news_sm",  # Danish
            "gik Diederik nu?",
            [
                SpacyMorph(lemma="gå", inflection="gik", part_of_speech="VERB"),
                SpacyMorph(
                    lemma="diederik", inflection="diederik", part_of_speech="PROPN"
                ),
                SpacyMorph(lemma="nu", inflection="nu", part_of_speech="ADV"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="gå", inflection="gik"),
                Morpheme(lemma="nu", inflection="nu"),
            ],
        ),
        (
            "sv_core_news_sm",  # Swedish
            "gick Astrid nu?",  # the sv model is terrible at proper nouns
            [
                SpacyMorph(lemma="gå", inflection="gick", part_of_speech="VERB"),
                SpacyMorph(lemma="astrid", inflection="astrid", part_of_speech="NOUN"),
                SpacyMorph(lemma="nu", inflection="nu", part_of_speech="ADV"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="gå", inflection="gick"),
                Morpheme(lemma="astrid", inflection="astrid"),
                Morpheme(lemma="nu", inflection="nu"),
            ],
        ),
        (
            "nl_core_news_sm",  # Dutch
            "Is Alexander weggelopen?",
            [
                SpacyMorph(lemma="zijn", inflection="is", part_of_speech="AUX"),
                SpacyMorph(
                    lemma="Alexander", inflection="alexander", part_of_speech="PROPN"
                ),
                SpacyMorph(
                    lemma="weggelopen", inflection="weggelopen", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="zijn", inflection="is"),
                Morpheme(lemma="weggelopen", inflection="weggelopen"),
            ],
        ),
        (
            "hr_core_news_sm",  # Croatian
            "Je li Krunoslav otišao?",
            [
                SpacyMorph(lemma="biti", inflection="je", part_of_speech="AUX"),
                SpacyMorph(lemma="li", inflection="li", part_of_speech="PART"),
                SpacyMorph(
                    lemma="krunoslav", inflection="krunoslav", part_of_speech="PROPN"
                ),
                SpacyMorph(lemma="otići", inflection="otišao", part_of_speech="VERB"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="biti", inflection="je"),
                Morpheme(lemma="li", inflection="li"),
                Morpheme(lemma="otići", inflection="otišao"),
            ],
        ),
        (
            "fi_core_news_sm",  # Finnish
            "kävelikö Aarne pois?",
            [
                SpacyMorph(
                    lemma="kävelikö", inflection="kävelikö", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="aarne", inflection="aarne", part_of_speech="PROPN"),
                SpacyMorph(lemma="pois", inflection="pois", part_of_speech="ADV"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="kävelikö", inflection="kävelikö"),
                Morpheme(lemma="pois", inflection="pois"),
            ],
        ),
        (
            "el_core_news_sm",  # Greek (modern)
            "έφυγε ο Άλεξ",
            [
                SpacyMorph(lemma="έφυγε", inflection="έφυγε", part_of_speech="VERB"),
                SpacyMorph(lemma="ο", inflection="ο", part_of_speech="DET"),
                SpacyMorph(lemma="άλεξ", inflection="άλεξ", part_of_speech="NOUN"),
            ],
            [
                Morpheme(lemma="έφυγε", inflection="έφυγε"),
                Morpheme(lemma="ο", inflection="ο"),
                Morpheme(lemma="άλεξ", inflection="άλεξ"),
            ],
        ),
        (
            "it_core_news_sm",  # Italian
            "Leonardo ha camminato?",
            [
                SpacyMorph(
                    lemma="leonardo", inflection="leonardo", part_of_speech="NOUN"
                ),
                SpacyMorph(lemma="avere", inflection="ha", part_of_speech="AUX"),
                SpacyMorph(
                    lemma="camminare", inflection="camminato", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="leonardo", inflection="leonardo"),
                Morpheme(lemma="avere", inflection="ha"),
                Morpheme(lemma="camminare", inflection="camminato"),
            ],
        ),
        (
            "lt_core_news_sm",  # Lithuanian
            "Kur jūs dirbate?",
            [
                SpacyMorph(lemma="kur", inflection="kur", part_of_speech="ADV"),
                SpacyMorph(lemma="jūs", inflection="jūs", part_of_speech="PRON"),
                SpacyMorph(
                    lemma="dirbate", inflection="dirbate", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="kur", inflection="kur"),
                Morpheme(lemma="jūs", inflection="jūs"),
                Morpheme(lemma="dirbate", inflection="dirbate"),
            ],
        ),
        (
            "mk_core_news_sm",  # Macedonian
            "дали Александар одеше?",
            [
                SpacyMorph(lemma="дали", inflection="дали", part_of_speech="SCONJ"),
                SpacyMorph(
                    lemma="александар", inflection="александар", part_of_speech="PROPN"
                ),
                SpacyMorph(lemma="одеше", inflection="одеше", part_of_speech="SPACE"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="SPACE"),
            ],
            [
                Morpheme(lemma="дали", inflection="дали"),
                Morpheme(lemma="одеше", inflection="одеше"),
            ],
        ),
        (
            "pl_core_news_sm",  # Polish
            "czy Zofia chodziła?",
            [
                SpacyMorph(lemma="czy", inflection="czy", part_of_speech="PART"),
                SpacyMorph(lemma="zofia", inflection="zofia", part_of_speech="PROPN"),
                SpacyMorph(
                    lemma="chodzić", inflection="chodziła", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="czy", inflection="czy"),
                Morpheme(lemma="chodzić", inflection="chodziła"),
            ],
        ),
        (
            "pt_core_news_sm",  # Portuguese
            "você caminhou?",
            [
                SpacyMorph(lemma="você", inflection="você", part_of_speech="PRON"),
                SpacyMorph(
                    lemma="caminhar", inflection="caminhou", part_of_speech="VERB"
                ),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="você", inflection="você"),
                Morpheme(lemma="caminhar", inflection="caminhou"),
            ],
        ),
        (
            "ro_core_news_sm",  # Romanian
            "a mers Maria?",
            [
                SpacyMorph(lemma="avea", inflection="a", part_of_speech="AUX"),
                SpacyMorph(lemma="merge", inflection="mers", part_of_speech="VERB"),
                SpacyMorph(lemma="Maria", inflection="maria", part_of_speech="PROPN"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="avea", inflection="a"),
                Morpheme(lemma="merge", inflection="mers"),
            ],
        ),
        (
            "sl_core_news_sm",  # Slovenian
            "je Luka hodil?",
            [
                SpacyMorph(lemma="biti", inflection="je", part_of_speech="AUX"),
                SpacyMorph(lemma="luka", inflection="luka", part_of_speech="PROPN"),
                SpacyMorph(lemma="hoditi", inflection="hodil", part_of_speech="VERB"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="biti", inflection="je"),
                Morpheme(lemma="hoditi", inflection="hodil"),
            ],
        ),
        (
            "ru_core_news_sm",  # Russian
            "Дмитрий ходил?",
            [
                SpacyMorph(
                    lemma="дмитрий", inflection="дмитрий", part_of_speech="PROPN"
                ),
                SpacyMorph(lemma="ходить", inflection="ходил", part_of_speech="VERB"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="ходить", inflection="ходил"),
            ],
        ),
        (
            "ko_core_news_sm",  # Korean
            "한동훈 장관을 추대했다.",
            [
                SpacyMorph(lemma="한동", inflection="한동훈", part_of_speech="PROPN"),
                SpacyMorph(lemma="장관", inflection="장관을", part_of_speech="NOUN"),
                SpacyMorph(lemma="추대", inflection="추대했다", part_of_speech="VERB"),
                SpacyMorph(lemma=".", inflection=".", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="장관", inflection="장관을"),
                Morpheme(lemma="추대", inflection="추대했다"),
            ],
        ),
        (
            "uk_core_news_sm",  # Ukrainian
            "Дмитро ходив?",
            [
                SpacyMorph(lemma="дмитро", inflection="дмитро", part_of_speech="PROPN"),
                SpacyMorph(lemma="ходити", inflection="ходив", part_of_speech="VERB"),
                SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="ходити", inflection="ходив"),
            ],
        ),
        (
            "zh_core_web_sm",  # Chinese
            "你能肯定吗？",
            [
                SpacyMorph(lemma="你", inflection="你", part_of_speech="PRON"),
                SpacyMorph(lemma="能", inflection="能", part_of_speech="VERB"),
                SpacyMorph(lemma="肯定", inflection="肯定", part_of_speech="VERB"),
                SpacyMorph(lemma="吗", inflection="吗", part_of_speech="PART"),
                SpacyMorph(lemma="？", inflection="？", part_of_speech="PUNCT"),
            ],
            [
                Morpheme(lemma="你", inflection="你"),
                Morpheme(lemma="能", inflection="能"),
                Morpheme(lemma="肯定", inflection="肯定"),
                Morpheme(lemma="吗", inflection="吗"),
            ],
        ),
    ],
)
def test_spacy(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
    spacy_model_name: str,
    sentence: str,
    expected_spacy_morphs: list[SpacyMorph],
    expected_am_morphs: list[Morpheme],
) -> None:
    nlp: Any = get_nlp(spacy_model_name=spacy_model_name)
    doc = nlp(sentence.lower())  # the recalc process lowercases like this
    assert len(doc) == len(expected_spacy_morphs)

    # for w in doc:
    #     print(f"w.lemma_: {w.lemma_}")
    #     print(f"w.text: {w.text}")
    #     print(f"w.pos_: {w.pos_}")
    #     print("")

    for index, w in enumerate(doc):
        morph: SpacyMorph = expected_spacy_morphs[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)

    # print(f"processes morphs: {len(processed_morphs)}")
    # for _morph in processed_morphs:
    #     print(f"base: {_morph.lemma}")
    #     print(f"inflected: {_morph.inflection}")
    #     print("")
    #
    # print(f"expected_am_morphs: {len(expected_am_morphs)}")
    # for _morph in expected_am_morphs:
    #     print(f"base: {_morph.lemma}")
    #     print(f"inflected: {_morph.inflection}")
    #     print("")

    assert processed_morphs == expected_am_morphs
