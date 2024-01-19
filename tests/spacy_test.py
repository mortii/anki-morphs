import json
from unittest import mock

import aqt
import pytest
import spacy

from ankimorphs import AnkiMorphsConfig, config, spacy_wrapper
from ankimorphs.morpheme import Morpheme
from ankimorphs.spacy_wrapper import get_nlp
from ankimorphs.text_preprocessing import get_processed_spacy_morphs


class SpacyMorph:
    def __init__(self, lemma: str, inflection: str, part_of_speech: str) -> None:
        self.lemma = lemma
        self.inflection = inflection
        self.part_of_speech = part_of_speech


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    print("fake environment initiated")
    mock_mw = mock.Mock(spec=aqt.mw)  # can use any mw to spec

    _config_data = None
    with open("ankimorphs/config.json", encoding="utf-8") as file:
        _config_data = json.load(file)

    mock_mw.addonManager.getConfig.return_value = _config_data
    patch_config_mw = mock.patch.object(config, "mw", mock_mw)
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    patch_config_mw.start()
    patch_testing_variable.start()
    yield
    patch_config_mw.stop()
    patch_testing_variable.stop()


def test_ja_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Japanese

    nlp: spacy.Language = get_nlp(spacy_model_name="ja_core_news_sm")
    expression = "半田さん　朝代わってよ"
    correct_spacy_morphs: list[SpacyMorph] = [
        SpacyMorph(lemma="半田", inflection="半田", part_of_speech="PROPN"),
        SpacyMorph(lemma="さん", inflection="さん", part_of_speech="NOUN"),
        SpacyMorph(lemma="　", inflection="　", part_of_speech="X"),
        SpacyMorph(lemma="朝", inflection="朝", part_of_speech="NOUN"),
        SpacyMorph(lemma="代わる", inflection="代わっ", part_of_speech="VERB"),
        SpacyMorph(lemma="て", inflection="て", part_of_speech="SCONJ"),
        SpacyMorph(lemma="よ", inflection="よ", part_of_speech="PART"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="さん", inflection="さん"),
        Morpheme(lemma="朝", inflection="朝"),
        Morpheme(lemma="代わる", inflection="代わっ"),
        Morpheme(lemma="て", inflection="て"),
        Morpheme(lemma="よ", inflection="よ"),
    ]

    doc = nlp(expression)
    assert len(doc) == 7

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_spacy_morphs[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_nb_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Norsk Bokmål

    nlp: spacy.Language = get_nlp(spacy_model_name="nb_core_news_sm")
    expression = "Gikk Harald nå?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="gå", inflection="gikk", part_of_speech="VERB"),
        SpacyMorph(lemma="harald", inflection="harald", part_of_speech="PROPN"),
        SpacyMorph(lemma="nå", inflection="nå", part_of_speech="ADV"),
        SpacyMorph(lemma="$?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="gå", inflection="gikk"),
        Morpheme(lemma="nå", inflection="nå"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_en_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # English

    nlp: spacy.Language = get_nlp(spacy_model_name="en_core_web_sm")
    expression = "At 3 o'clock, Harry's mother-in-law walked away.".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="at", inflection="at", part_of_speech="ADP"),
        SpacyMorph(lemma="3", inflection="3", part_of_speech="NUM"),
        SpacyMorph(lemma="o'clock", inflection="o'clock", part_of_speech="NOUN"),
        SpacyMorph(lemma=",", inflection=",", part_of_speech="PUNCT"),
        SpacyMorph(lemma="harry", inflection="harry", part_of_speech="PROPN"),
        SpacyMorph(lemma="'s", inflection="'s", part_of_speech="PART"),
        SpacyMorph(
            lemma="mother-in-law", inflection="mother-in-law", part_of_speech="NOUN"
        ),
        SpacyMorph(lemma="walk", inflection="walked", part_of_speech="VERB"),
        SpacyMorph(lemma="away", inflection="away", part_of_speech="ADV"),
        SpacyMorph(lemma=".", inflection=".", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="at", inflection="at"),
        Morpheme(lemma="3", inflection="3"),
        Morpheme(lemma="o'clock", inflection="o'clock"),
        Morpheme(lemma="'s", inflection="'s"),
        Morpheme(lemma="mother-in-law", inflection="mother-in-law"),
        Morpheme(lemma="walk", inflection="walked"),
        Morpheme(lemma="away", inflection="away"),
    ]
    doc = nlp(expression)
    assert len(doc) == 10

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)

    # print(f"processes morphs: {len(processed_morphs)}")
    # for _morph in processed_morphs:
    #     print(f"base: {_morph.base}")
    #     print(f"inflected: {_morph.inflected}")

    assert processed_morphs == correct_am_morphs


def test_de_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # German

    nlp: spacy.Language = get_nlp(
        spacy_model_name="de_core_news_md"  # sm model is worse
    )
    expression = "»Was ist los?«Harry schüttelte den Kopf und spähte.".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="--", inflection="»", part_of_speech="PUNCT"),
        SpacyMorph(lemma="was", inflection="was", part_of_speech="PRON"),  # wrong...
        SpacyMorph(lemma="sein", inflection="ist", part_of_speech="AUX"),
        SpacyMorph(lemma="los", inflection="los", part_of_speech="ADV"),
        SpacyMorph(lemma="--", inflection="?", part_of_speech="PUNCT"),
        SpacyMorph(lemma="--", inflection="«", part_of_speech="PUNCT"),
        SpacyMorph(lemma="Harry", inflection="harry", part_of_speech="PROPN"),
        SpacyMorph(lemma="schüttelen", inflection="schüttelte", part_of_speech="VERB"),
        SpacyMorph(lemma="der", inflection="den", part_of_speech="DET"),
        SpacyMorph(lemma="Kopf", inflection="kopf", part_of_speech="NOUN"),
        SpacyMorph(lemma="und", inflection="und", part_of_speech="CCONJ"),
        SpacyMorph(lemma="spähen", inflection="spähte", part_of_speech="VERB"),
        SpacyMorph(lemma="--", inflection=".", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="was", inflection="was"),
        Morpheme(lemma="sein", inflection="ist"),
        Morpheme(lemma="los", inflection="los"),
        Morpheme(lemma="schüttelen", inflection="schüttelte"),
        Morpheme(lemma="der", inflection="den"),
        Morpheme(lemma="Kopf", inflection="kopf"),
        Morpheme(lemma="und", inflection="und"),
        Morpheme(lemma="spähen", inflection="spähte"),
    ]

    doc = nlp(expression)
    assert len(doc) == 13

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ca_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Catalan

    nlp: spacy.Language = get_nlp(spacy_model_name="ca_core_news_sm")
    # bad at proper nouns
    expression = "va caminar en Guillem?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="anar", inflection="va", part_of_speech="AUX"),
        SpacyMorph(lemma="caminar", inflection="caminar", part_of_speech="VERB"),
        SpacyMorph(lemma="en", inflection="en", part_of_speech="ADP"),
        SpacyMorph(lemma="guillem", inflection="guillem", part_of_speech="NOUN"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="anar", inflection="va"),
        Morpheme(lemma="caminar", inflection="caminar"),
        Morpheme(lemma="en", inflection="en"),
        Morpheme(lemma="guillem", inflection="guillem"),
    ]

    doc = nlp(expression)
    assert len(doc) == 5

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_es_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Spanish

    nlp: spacy.Language = get_nlp(spacy_model_name="es_core_news_sm")
    expression = "¿Pedro ya comió?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="¿", inflection="¿", part_of_speech="PUNCT"),
        SpacyMorph(lemma="pedro", inflection="pedro", part_of_speech="PROPN"),
        SpacyMorph(lemma="ya", inflection="ya", part_of_speech="ADV"),
        SpacyMorph(lemma="comer", inflection="comió", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="ya", inflection="ya"),
        Morpheme(lemma="comer", inflection="comió"),
    ]

    doc = nlp(expression)
    assert len(doc) == 5

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_fr_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # French

    nlp: spacy.Language = get_nlp(spacy_model_name="fr_core_news_sm")
    expression = "Ça m’est égal?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="cela", inflection="ça", part_of_speech="PRON"),
        SpacyMorph(lemma="m’est", inflection="m’est", part_of_speech="NOUN"),
        SpacyMorph(lemma="égal", inflection="égal", part_of_speech="ADJ"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="cela", inflection="ça"),
        Morpheme(lemma="m’est", inflection="m’est"),
        Morpheme(lemma="égal", inflection="égal"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_da_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Danish

    nlp: spacy.Language = get_nlp(spacy_model_name="da_core_news_sm")
    expression = "gik Diederik nu?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="gå", inflection="gik", part_of_speech="VERB"),
        SpacyMorph(lemma="diederik", inflection="diederik", part_of_speech="PROPN"),
        SpacyMorph(lemma="nu", inflection="nu", part_of_speech="ADV"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="gå", inflection="gik"),
        Morpheme(lemma="nu", inflection="nu"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_sv_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Swedish

    nlp: spacy.Language = get_nlp(spacy_model_name="sv_core_news_sm")
    expression = "gick Astrid nu?".lower()  # the sv model is terrible at proper nouns

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="gå", inflection="gick", part_of_speech="VERB"),
        SpacyMorph(lemma="astrid", inflection="astrid", part_of_speech="NOUN"),
        SpacyMorph(lemma="nu", inflection="nu", part_of_speech="ADV"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="gå", inflection="gick"),
        Morpheme(lemma="astrid", inflection="astrid"),
        Morpheme(lemma="nu", inflection="nu"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_nl_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Dutch

    nlp: spacy.Language = get_nlp(spacy_model_name="nl_core_news_sm")
    expression = "Is Lucas weggelopen?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="zijn", inflection="is", part_of_speech="AUX"),
        SpacyMorph(lemma="lucas", inflection="lucas", part_of_speech="PROPN"),
        SpacyMorph(lemma="weggelopen", inflection="weggelopen", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="zijn", inflection="is"),
        Morpheme(lemma="weggelopen", inflection="weggelopen"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_hr_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Croatian

    nlp: spacy.Language = get_nlp(spacy_model_name="hr_core_news_sm")
    # hr model is bad at recognizing proper nouns
    expression = "Je li Krunoslav otišao?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="biti", inflection="je", part_of_speech="AUX"),
        SpacyMorph(lemma="li", inflection="li", part_of_speech="PART"),
        SpacyMorph(lemma="krunoslav", inflection="krunoslav", part_of_speech="NOUN"),
        SpacyMorph(lemma="otići", inflection="otišao", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="biti", inflection="je"),
        Morpheme(lemma="li", inflection="li"),
        Morpheme(lemma="krunoslav", inflection="krunoslav"),
        Morpheme(lemma="otići", inflection="otišao"),
    ]

    doc = nlp(expression)
    assert len(doc) == 5

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_fi_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Finnish

    nlp: spacy.Language = get_nlp(spacy_model_name="fi_core_news_sm")
    expression = "kävelikö Aarne pois?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="kävelikö", inflection="kävelikö", part_of_speech="VERB"),
        SpacyMorph(lemma="aarne", inflection="aarne", part_of_speech="PROPN"),
        SpacyMorph(lemma="pois", inflection="pois", part_of_speech="ADV"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="kävelikö", inflection="kävelikö"),
        Morpheme(lemma="pois", inflection="pois"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_el_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Greek

    nlp: spacy.Language = get_nlp(spacy_model_name="el_core_news_sm")
    # gl model is not great at proper nouns
    expression = "έφυγε ο Άλεξ".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="έφυγε", inflection="έφυγε", part_of_speech="VERB"),
        SpacyMorph(lemma="ο", inflection="ο", part_of_speech="DET"),
        SpacyMorph(lemma="άλεξ", inflection="άλεξ", part_of_speech="NOUN"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="έφυγε", inflection="έφυγε"),
        Morpheme(lemma="ο", inflection="ο"),
        Morpheme(lemma="άλεξ", inflection="άλεξ"),
    ]

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_it_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Italian

    nlp: spacy.Language = get_nlp(spacy_model_name="it_core_news_sm")
    # it model is not great at proper nouns
    expression = "Leonardo ha camminato?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="leonardo", inflection="leonardo", part_of_speech="NOUN"),
        SpacyMorph(lemma="avere", inflection="ha", part_of_speech="AUX"),
        SpacyMorph(lemma="camminare", inflection="camminato", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="leonardo", inflection="leonardo"),
        Morpheme(lemma="avere", inflection="ha"),
        Morpheme(lemma="camminare", inflection="camminato"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_lt_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Lithuanian

    nlp: spacy.Language = get_nlp(spacy_model_name="lt_core_news_sm")
    expression = "Kur jūs dirbate?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="kur", inflection="kur", part_of_speech="ADV"),
        SpacyMorph(lemma="jūs", inflection="jūs", part_of_speech="PRON"),
        SpacyMorph(lemma="dirbate", inflection="dirbate", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="kur", inflection="kur"),
        Morpheme(lemma="jūs", inflection="jūs"),
        Morpheme(lemma="dirbate", inflection="dirbate"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_mk_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Macedonian

    nlp: spacy.Language = get_nlp(spacy_model_name="mk_core_news_sm")
    expression = "дали Александар одеше?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="дали", inflection="дали", part_of_speech="SCONJ"),
        SpacyMorph(lemma="александар", inflection="александар", part_of_speech="PROPN"),
        SpacyMorph(lemma="одеше", inflection="одеше", part_of_speech="SPACE"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="SPACE"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="дали", inflection="дали"),
        Morpheme(lemma="одеше", inflection="одеше"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_pl_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Polish

    nlp: spacy.Language = get_nlp(spacy_model_name="pl_core_news_sm")
    expression = "czy Zofia chodziła?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="czy", inflection="czy", part_of_speech="PART"),
        SpacyMorph(lemma="zofia", inflection="zofia", part_of_speech="PROPN"),
        SpacyMorph(lemma="chodzić", inflection="chodziła", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="czy", inflection="czy"),
        Morpheme(lemma="chodzić", inflection="chodziła"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_pt_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Portuguese

    nlp: spacy.Language = get_nlp(spacy_model_name="pt_core_news_sm")
    # not great at proper nouns
    expression = "você caminhou?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="você", inflection="você", part_of_speech="PRON"),
        SpacyMorph(lemma="caminhar", inflection="caminhou", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="você", inflection="você"),
        Morpheme(lemma="caminhar", inflection="caminhou"),
    ]

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ro_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Romanian

    nlp: spacy.Language = get_nlp(spacy_model_name="ro_core_news_sm")
    expression = "a mers Maria?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="avea", inflection="a", part_of_speech="AUX"),
        SpacyMorph(lemma="merge", inflection="mers", part_of_speech="VERB"),
        SpacyMorph(lemma="Maria", inflection="maria", part_of_speech="PROPN"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="avea", inflection="a"),
        Morpheme(lemma="merge", inflection="mers"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_sl_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Slovenian

    nlp: spacy.Language = get_nlp(spacy_model_name="sl_core_news_sm")
    expression = "je Luka hodil?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="biti", inflection="je", part_of_speech="AUX"),
        SpacyMorph(lemma="luka", inflection="luka", part_of_speech="PROPN"),
        SpacyMorph(lemma="hoditi", inflection="hodil", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="biti", inflection="je"),
        Morpheme(lemma="hoditi", inflection="hodil"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ru_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Russian

    nlp: spacy.Language = get_nlp(spacy_model_name="ru_core_news_sm")
    expression = "Дмитрий ходил?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="дмитрий", inflection="дмитрий", part_of_speech="PROPN"),
        SpacyMorph(lemma="ходить", inflection="ходил", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="ходить", inflection="ходил"),
    ]

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_uk_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Ukrainian

    nlp: spacy.Language = get_nlp(spacy_model_name="uk_core_news_sm")
    expression = "Дмитро ходив?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="дмитро", inflection="дмитро", part_of_speech="PROPN"),
        SpacyMorph(lemma="ходити", inflection="ходив", part_of_speech="VERB"),
        SpacyMorph(lemma="?", inflection="?", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="ходити", inflection="ходив"),
    ]

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ko_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Korean

    nlp: spacy.Language = get_nlp(spacy_model_name="ko_core_news_sm")
    expression = "한동훈 장관을 추대했다.".lower()
    # expression = "눌러".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="한동", inflection="한동훈", part_of_speech="PROPN"),
        SpacyMorph(lemma="장관", inflection="장관을", part_of_speech="NOUN"),
        SpacyMorph(lemma="추대", inflection="추대했다", part_of_speech="VERB"),
        SpacyMorph(lemma=".", inflection=".", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="장관", inflection="장관을"),
        Morpheme(lemma="추대", inflection="추대했다"),
    ]

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_zh_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Chinese

    nlp: spacy.Language = get_nlp(spacy_model_name="zh_core_web_sm")
    expression = "你能肯定吗？".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(lemma="你", inflection="你", part_of_speech="PRON"),
        SpacyMorph(lemma="能", inflection="能", part_of_speech="VERB"),
        SpacyMorph(lemma="肯定", inflection="肯定", part_of_speech="VERB"),
        SpacyMorph(lemma="吗", inflection="吗", part_of_speech="PART"),
        SpacyMorph(lemma="？", inflection="？", part_of_speech="PUNCT"),
    ]
    correct_am_morphs: list[Morpheme] = [
        Morpheme(lemma="你", inflection="你"),
        Morpheme(lemma="能", inflection="能"),
        Morpheme(lemma="肯定", inflection="肯定"),
        Morpheme(lemma="吗", inflection="吗"),
    ]

    doc = nlp(expression)
    assert len(doc) == 5

    # for w in doc:
    #     print(f"w.lemma_: {w.lemma_}")
    #     print(f"w.text: {w.text}")
    #     print(f"w.pos_: {w.pos_}")
    #     print("")

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflection == w.text
        assert morph.lemma == w.lemma_
        assert morph.part_of_speech == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: list[Morpheme] = get_processed_spacy_morphs(am_config, doc)

    # print(f"processes morphs: {len(processed_morphs)}")
    # for _morph in processed_morphs:
    #     print(f"base: {_morph.base}")
    #     print(f"inflected: {_morph.inflected}")
    #     print("")

    assert processed_morphs == correct_am_morphs
