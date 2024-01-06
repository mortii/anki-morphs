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
    def __init__(self, base: str, inflected: str, pos: str) -> None:
        self.base = base
        self.inflected = inflected
        self.pos = pos


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
        SpacyMorph(base="半田", inflected="半田", pos="PROPN"),
        SpacyMorph(base="さん", inflected="さん", pos="NOUN"),
        SpacyMorph(base="　", inflected="　", pos="X"),
        SpacyMorph(base="朝", inflected="朝", pos="NOUN"),
        SpacyMorph(base="代わる", inflected="代わっ", pos="VERB"),
        SpacyMorph(base="て", inflected="て", pos="SCONJ"),
        SpacyMorph(base="よ", inflected="よ", pos="PART"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="さん", inflected="さん"),
        Morpheme(base="朝", inflected="朝"),
        Morpheme(base="代わる", inflected="代わっ"),
        Morpheme(base="て", inflected="て"),
        Morpheme(base="よ", inflected="よ"),
    }

    doc = nlp(expression)
    assert len(doc) == 7

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_spacy_morphs[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_nb_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Norsk Bokmål

    nlp: spacy.Language = get_nlp(spacy_model_name="nb_core_news_sm")
    expression = "Gikk Harald nå?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="gå", inflected="gikk", pos="VERB"),
        SpacyMorph(base="harald", inflected="harald", pos="PROPN"),
        SpacyMorph(base="nå", inflected="nå", pos="ADV"),
        SpacyMorph(base="$?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="gå", inflected="gikk"),
        Morpheme(base="nå", inflected="nå"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_en_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # English

    nlp: spacy.Language = get_nlp(spacy_model_name="en_core_web_sm")
    expression = "At 3 o'clock, Harry's mother-in-law walked away.".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="at", inflected="at", pos="ADP"),
        SpacyMorph(base="3", inflected="3", pos="NUM"),
        SpacyMorph(base="o'clock", inflected="o'clock", pos="NOUN"),
        SpacyMorph(base=",", inflected=",", pos="PUNCT"),
        SpacyMorph(base="harry", inflected="harry", pos="PROPN"),
        SpacyMorph(base="'s", inflected="'s", pos="PART"),
        SpacyMorph(base="mother-in-law", inflected="mother-in-law", pos="NOUN"),
        SpacyMorph(base="walk", inflected="walked", pos="VERB"),
        SpacyMorph(base="away", inflected="away", pos="ADV"),
        SpacyMorph(base=".", inflected=".", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="at", inflected="at"),
        Morpheme(base="3", inflected="3"),
        Morpheme(base="o'clock", inflected="o'clock"),
        Morpheme(base="'s", inflected="'s"),
        Morpheme(base="mother-in-law", inflected="mother-in-law"),
        Morpheme(base="walk", inflected="walked"),
        Morpheme(base="away", inflected="away"),
    }
    doc = nlp(expression)
    assert len(doc) == 10

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)

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
        SpacyMorph(base="--", inflected="»", pos="PUNCT"),
        SpacyMorph(base="was", inflected="was", pos="PRON"),  # wrong...
        SpacyMorph(base="sein", inflected="ist", pos="AUX"),
        SpacyMorph(base="los", inflected="los", pos="ADV"),
        SpacyMorph(base="--", inflected="?", pos="PUNCT"),
        SpacyMorph(base="--", inflected="«", pos="PUNCT"),
        SpacyMorph(base="Harry", inflected="harry", pos="PROPN"),
        SpacyMorph(base="schüttelen", inflected="schüttelte", pos="VERB"),
        SpacyMorph(base="der", inflected="den", pos="DET"),
        SpacyMorph(base="Kopf", inflected="kopf", pos="NOUN"),
        SpacyMorph(base="und", inflected="und", pos="CCONJ"),
        SpacyMorph(base="spähen", inflected="spähte", pos="VERB"),
        SpacyMorph(base="--", inflected=".", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="was", inflected="was"),  # TODO wrong?
        Morpheme(base="sein", inflected="ist"),
        Morpheme(base="los", inflected="los"),
        Morpheme(base="schüttelen", inflected="schüttelte"),
        Morpheme(base="der", inflected="den"),
        Morpheme(base="Kopf", inflected="kopf"),
        Morpheme(base="und", inflected="und"),
        Morpheme(base="spähen", inflected="spähte"),
    }

    doc = nlp(expression)
    assert len(doc) == 13

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ca_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Catalan

    nlp: spacy.Language = get_nlp(spacy_model_name="ca_core_news_sm")
    # bad at proper nouns
    expression = "va caminar en Guillem?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="anar", inflected="va", pos="AUX"),
        SpacyMorph(base="caminar", inflected="caminar", pos="VERB"),
        SpacyMorph(base="en", inflected="en", pos="ADP"),
        SpacyMorph(base="guillem", inflected="guillem", pos="NOUN"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="anar", inflected="va"),
        Morpheme(base="caminar", inflected="caminar"),
        Morpheme(base="en", inflected="en"),
        Morpheme(base="guillem", inflected="guillem"),
    }

    doc = nlp(expression)
    assert len(doc) == 5

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_es_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Spanish

    nlp: spacy.Language = get_nlp(spacy_model_name="es_core_news_sm")
    expression = "¿Pedro ya comió?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="¿", inflected="¿", pos="PUNCT"),
        SpacyMorph(base="pedro", inflected="pedro", pos="PROPN"),
        SpacyMorph(base="ya", inflected="ya", pos="ADV"),
        SpacyMorph(base="comer", inflected="comió", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="ya", inflected="ya"),
        Morpheme(base="comer", inflected="comió"),
    }

    doc = nlp(expression)
    assert len(doc) == 5

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_fr_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # French

    nlp: spacy.Language = get_nlp(spacy_model_name="fr_core_news_sm")
    expression = "Ça m’est égal?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="cela", inflected="ça", pos="PRON"),
        SpacyMorph(base="m’est", inflected="m’est", pos="NOUN"),
        SpacyMorph(base="égal", inflected="égal", pos="ADJ"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="cela", inflected="ça"),
        Morpheme(base="m’est", inflected="m’est"),
        Morpheme(base="égal", inflected="égal"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_da_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Danish

    nlp: spacy.Language = get_nlp(spacy_model_name="da_core_news_sm")
    expression = "gik Diederik nu?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="gå", inflected="gik", pos="VERB"),
        SpacyMorph(base="diederik", inflected="diederik", pos="PROPN"),
        SpacyMorph(base="nu", inflected="nu", pos="ADV"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="gå", inflected="gik"),
        Morpheme(base="nu", inflected="nu"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_sv_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Swedish

    nlp: spacy.Language = get_nlp(spacy_model_name="sv_core_news_sm")
    expression = "gick Astrid nu?".lower()  # the sv model is terrible at proper nouns

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="gå", inflected="gick", pos="VERB"),
        SpacyMorph(base="astrid", inflected="astrid", pos="NOUN"),
        SpacyMorph(base="nu", inflected="nu", pos="ADV"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="gå", inflected="gick"),
        Morpheme(base="astrid", inflected="astrid"),
        Morpheme(base="nu", inflected="nu"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_nl_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Dutch

    nlp: spacy.Language = get_nlp(spacy_model_name="nl_core_news_sm")
    expression = "Is Lucas weggelopen?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="zijn", inflected="is", pos="AUX"),
        SpacyMorph(base="lucas", inflected="lucas", pos="PROPN"),
        SpacyMorph(base="weggelopen", inflected="weggelopen", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="zijn", inflected="is"),
        Morpheme(base="weggelopen", inflected="weggelopen"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_hr_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Croatian

    nlp: spacy.Language = get_nlp(spacy_model_name="hr_core_news_sm")
    # hr model is bad at recognizing proper nouns
    expression = "Je li Krunoslav otišao?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="biti", inflected="je", pos="AUX"),
        SpacyMorph(base="li", inflected="li", pos="PART"),
        SpacyMorph(base="krunoslav", inflected="krunoslav", pos="NOUN"),
        SpacyMorph(base="otići", inflected="otišao", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="biti", inflected="je"),
        Morpheme(base="li", inflected="li"),
        Morpheme(base="krunoslav", inflected="krunoslav"),
        Morpheme(base="otići", inflected="otišao"),
    }

    doc = nlp(expression)
    assert len(doc) == 5

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_fi_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Finnish

    nlp: spacy.Language = get_nlp(spacy_model_name="fi_core_news_sm")
    expression = "kävelikö Aarne pois?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="kävelikö", inflected="kävelikö", pos="VERB"),
        SpacyMorph(base="aarne", inflected="aarne", pos="PROPN"),
        SpacyMorph(base="pois", inflected="pois", pos="ADV"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="kävelikö", inflected="kävelikö"),
        Morpheme(base="pois", inflected="pois"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_el_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Greek

    nlp: spacy.Language = get_nlp(spacy_model_name="el_core_news_sm")
    # gl model is not great at proper nouns
    expression = "έφυγε ο Άλεξ".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="έφυγε", inflected="έφυγε", pos="VERB"),
        SpacyMorph(base="ο", inflected="ο", pos="DET"),
        SpacyMorph(base="άλεξ", inflected="άλεξ", pos="NOUN"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="έφυγε", inflected="έφυγε"),
        Morpheme(base="ο", inflected="ο"),
        Morpheme(base="άλεξ", inflected="άλεξ"),
    }

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_it_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Italian

    nlp: spacy.Language = get_nlp(spacy_model_name="it_core_news_sm")
    # it model is not great at proper nouns
    expression = "Leonardo ha camminato?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="leonardo", inflected="leonardo", pos="NOUN"),
        SpacyMorph(base="avere", inflected="ha", pos="AUX"),
        SpacyMorph(base="camminare", inflected="camminato", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="leonardo", inflected="leonardo"),
        Morpheme(base="avere", inflected="ha"),
        Morpheme(base="camminare", inflected="camminato"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_lt_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Lithuanian

    nlp: spacy.Language = get_nlp(spacy_model_name="lt_core_news_sm")
    expression = "Kur jūs dirbate?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="kur", inflected="kur", pos="ADV"),
        SpacyMorph(base="jūs", inflected="jūs", pos="PRON"),
        SpacyMorph(base="dirbate", inflected="dirbate", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="kur", inflected="kur"),
        Morpheme(base="jūs", inflected="jūs"),
        Morpheme(base="dirbate", inflected="dirbate"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_mk_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Macedonian

    nlp: spacy.Language = get_nlp(spacy_model_name="mk_core_news_sm")
    expression = "дали Александар одеше?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="дали", inflected="дали", pos="SCONJ"),
        SpacyMorph(base="александар", inflected="александар", pos="PROPN"),
        SpacyMorph(base="одеше", inflected="одеше", pos="SPACE"),
        SpacyMorph(base="?", inflected="?", pos="SPACE"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="дали", inflected="дали"),
        Morpheme(base="одеше", inflected="одеше"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_pl_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Polish

    nlp: spacy.Language = get_nlp(spacy_model_name="pl_core_news_sm")
    expression = "czy Zofia chodziła?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="czy", inflected="czy", pos="PART"),
        SpacyMorph(base="zofia", inflected="zofia", pos="PROPN"),
        SpacyMorph(base="chodzić", inflected="chodziła", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="czy", inflected="czy"),
        Morpheme(base="chodzić", inflected="chodziła"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_pt_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Portuguese

    nlp: spacy.Language = get_nlp(spacy_model_name="pt_core_news_sm")
    # not great at proper nouns
    expression = "você caminhou?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="você", inflected="você", pos="PRON"),
        SpacyMorph(base="caminhar", inflected="caminhou", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="você", inflected="você"),
        Morpheme(base="caminhar", inflected="caminhou"),
    }

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ro_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Romanian

    nlp: spacy.Language = get_nlp(spacy_model_name="ro_core_news_sm")
    expression = "a mers Maria?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="avea", inflected="a", pos="AUX"),
        SpacyMorph(base="merge", inflected="mers", pos="VERB"),
        SpacyMorph(base="Maria", inflected="maria", pos="PROPN"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="avea", inflected="a"),
        Morpheme(base="merge", inflected="mers"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_sl_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Slovenian

    nlp: spacy.Language = get_nlp(spacy_model_name="sl_core_news_sm")
    expression = "je Luka hodil?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="biti", inflected="je", pos="AUX"),
        SpacyMorph(base="luka", inflected="luka", pos="PROPN"),
        SpacyMorph(base="hoditi", inflected="hodil", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="biti", inflected="je"),
        Morpheme(base="hoditi", inflected="hodil"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ru_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Russian

    nlp: spacy.Language = get_nlp(spacy_model_name="ru_core_news_sm")
    expression = "Дмитрий ходил?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="дмитрий", inflected="дмитрий", pos="PROPN"),
        SpacyMorph(base="ходить", inflected="ходил", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="ходить", inflected="ходил"),
    }

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_uk_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Ukrainian

    nlp: spacy.Language = get_nlp(spacy_model_name="uk_core_news_sm")
    expression = "Дмитро ходив?".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="дмитро", inflected="дмитро", pos="PROPN"),
        SpacyMorph(base="ходити", inflected="ходив", pos="VERB"),
        SpacyMorph(base="?", inflected="?", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="ходити", inflected="ходив"),
    }

    doc = nlp(expression)
    assert len(doc) == 3

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_ko_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Korean

    nlp: spacy.Language = get_nlp(spacy_model_name="ko_core_news_sm")
    expression = "한동훈 장관을 추대했다.".lower()
    # expression = "눌러".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="한동", inflected="한동훈", pos="PROPN"),
        SpacyMorph(base="장관", inflected="장관을", pos="NOUN"),
        SpacyMorph(base="추대", inflected="추대했다", pos="VERB"),
        SpacyMorph(base=".", inflected=".", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="장관", inflected="장관을"),
        Morpheme(base="추대", inflected="추대했다"),
    }

    doc = nlp(expression)
    assert len(doc) == 4

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    am_config.preprocess_ignore_names_morphemizer = True
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)
    assert processed_morphs == correct_am_morphs


def test_zh_model(fake_environment) -> None:  # pylint:disable=unused-argument
    # Chinese

    nlp: spacy.Language = get_nlp(spacy_model_name="zh_core_web_sm")
    expression = "你能肯定吗？".lower()

    correct_output: list[SpacyMorph] = [
        SpacyMorph(base="你", inflected="你", pos="PRON"),
        SpacyMorph(base="能", inflected="能", pos="VERB"),
        SpacyMorph(base="肯定", inflected="肯定", pos="VERB"),
        SpacyMorph(base="吗", inflected="吗", pos="PART"),
        SpacyMorph(base="？", inflected="？", pos="PUNCT"),
    ]
    correct_am_morphs: set[Morpheme] = {
        Morpheme(base="你", inflected="你"),
        Morpheme(base="能", inflected="能"),
        Morpheme(base="肯定", inflected="肯定"),
        Morpheme(base="吗", inflected="吗"),
    }

    doc = nlp(expression)
    assert len(doc) == 5

    # for w in doc:
    #     print(f"w.lemma_: {w.lemma_}")
    #     print(f"w.text: {w.text}")
    #     print(f"w.pos_: {w.pos_}")
    #     print("")

    for index, w in enumerate(doc):
        morph: SpacyMorph = correct_output[index]
        assert morph.inflected == w.text
        assert morph.base == w.lemma_
        assert morph.pos == w.pos_

    am_config = AnkiMorphsConfig()
    processed_morphs: set[Morpheme] = get_processed_spacy_morphs(am_config, doc)

    # print(f"processes morphs: {len(processed_morphs)}")
    # for _morph in processed_morphs:
    #     print(f"base: {_morph.base}")
    #     print(f"inflected: {_morph.inflected}")
    #     print("")

    assert processed_morphs == correct_am_morphs
