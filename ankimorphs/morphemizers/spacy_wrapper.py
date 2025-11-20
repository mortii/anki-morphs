from __future__ import annotations

import functools
import os.path
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from anki.utils import is_win
from aqt import mw
from aqt.package import venv_binary

# pylint: disable=invalid-name

updated_python_path: bool = False
testing_environment: bool = False
successful_import: bool = False

_spacy: ModuleType | None = None
_spacy_utils: ModuleType | None = None  #  spacy.util

_SpacyLanguage: Any = None  #  spacy.language
_SpacyTokenizer: Any = None  # spacy.tokenizer
_SpacyDoc: Any = None  #  spacy.tokens.doc

# pylint: enable=invalid-name

# spaCy does not have a cli to query available languages or models, so we hardcode it.
available_langs_and_models: dict[str, list[str]] = {
    # fmt: off
    "Catalan": ["ca_core_news_sm", "ca_core_news_md", "ca_core_news_lg"],
    "Chinese": ["zh_core_web_sm", "zh_core_web_md", "zh_core_web_lg"],
    "Croatian": ["hr_core_news_sm", "hr_core_news_md", "hr_core_news_lg"],
    "Danish": ["da_core_news_sm", "da_core_news_md", "da_core_news_lg"],
    "Dutch": ["nl_core_news_sm", "nl_core_news_md", "nl_core_news_lg"],
    "English": ["en_core_web_sm", "en_core_web_md", "en_core_web_lg"],
    "Finnish": ["fi_core_news_sm", "fi_core_news_md", "fi_core_news_lg"],
    "French": ["fr_core_news_sm", "fr_core_news_md", "fr_core_news_lg"],
    "German": ["de_core_news_sm", "de_core_news_md", "de_core_news_lg"],
    "Greek": ["el_core_news_sm", "el_core_news_md", "el_core_news_lg"],
    "Italian": ["it_core_news_sm", "it_core_news_md", "it_core_news_lg"],
    "Japanese": ["ja_core_news_sm", "ja_core_news_md", "ja_core_news_lg"],
    "Korean": ["ko_core_news_sm", "ko_core_news_md", "ko_core_news_lg"],
    "Lithuanian": ["lt_core_news_sm", "lt_core_news_md", "lt_core_news_lg"],
    "Macedonian": ["mk_core_news_sm", "mk_core_news_md", "mk_core_news_lg"],
    "Norwegian Bokmål": ["nb_core_news_sm", "nb_core_news_md", "nb_core_news_lg"],
    "Polish": ["pl_core_news_sm", "pl_core_news_md", "pl_core_news_lg"],
    "Portuguese": ["pt_core_news_sm", "pt_core_news_md", "pt_core_news_lg"],
    "Romanian": ["ro_core_news_sm", "ro_core_news_md", "ro_core_news_lg"],
    "Russian": ["ru_core_news_sm", "ru_core_news_md", "ru_core_news_lg"],
    "Slovenian": ["sl_core_news_sm", "sl_core_news_md", "sl_core_news_lg"],
    "Spanish": ["es_core_news_sm", "es_core_news_md", "es_core_news_lg"],
    "Swedish": ["sv_core_news_sm", "sv_core_news_md", "sv_core_news_lg"],
    "Ukrainian": ["uk_core_news_sm", "uk_core_news_md", "uk_core_news_lg"],
    # fmt: on
}


LANGUAGE_PIPE_CONFIGS: dict[str, set[str]] = {
    "ca": {"tok2vec", "morphologizer", "lemmatizer"},
    "zh": {"tok2vec", "tagger", "attribute_ruler"},
    "hr": {"tok2vec", "lemmatizer", "morphologizer"},
    "da": {"tok2vec", "morphologizer", "lemmatizer"},
    "nl": {"tok2vec", "lemmatizer", "morphologizer"},
    "en": {"tok2vec", "tagger", "attribute_ruler", "lemmatizer", "morphologizer"},
    "fi": {"tok2vec", "lemmatizer", "morphologizer"},
    "fr": {"tok2vec", "lemmatizer", "morphologizer"},
    "de": {"tok2vec", "lemmatizer", "morphologizer"},
    "el": {"tok2vec", "lemmatizer", "morphologizer"},
    "it": {"tok2vec", "lemmatizer", "morphologizer"},
    "ja": {""},  # Japanese uses SudachiPy
    "ko": {"tok2vec", "morphologizer", "lemmatizer"},
    "lt": {"tok2vec", "lemmatizer", "morphologizer"},
    "mk": {"tok2vec", "lemmatizer", "morphologizer"},
    "nb": {"tok2vec", "attribute_ruler", "lemmatizer", "morphologizer", "ner"},
    "pl": {"tok2vec", "lemmatizer", "morphologizer"},
    "pt": {"tok2vec", "lemmatizer", "morphologizer"},
    "ro": {"tok2vec", "tagger", "morphologizer", "lemmatizer", "attribute_ruler"},
    "ru": {"tok2vec", "morphologizer", "lemmatizer"},
    "sl": {"tok2vec", "lemmatizer", "morphologizer"},
    "es": {"tok2vec", "lemmatizer", "morphologizer"},
    "sv": {"tok2vec", "lemmatizer", "morphologizer"},
    "uk": {"tok2vec", "morphologizer", "lemmatizer"},
}


def load_spacy_modules() -> None:
    # We load the spacy modules in this complicated way to maintain at least
    # some form of static type checking, and to minimize error checking
    # and exception handling

    global updated_python_path
    global successful_import
    global _spacy
    global _SpacyLanguage
    global _SpacyTokenizer
    global _SpacyDoc
    global _spacy_utils

    # dev environments should already have spaCy, so this can be skipped
    if not updated_python_path and not testing_environment:
        assert mw is not None

        spacy_path = _get_am_spacy_venv_path()

        if is_win is True:
            spacy_site_packages_path = os.path.join(spacy_path, "Lib", "site-packages")
        else:
            spacy_site_packages_path = os.path.join(
                spacy_path,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )

        # appending to the path is less disruptive than prepending
        sys.path.append(spacy_site_packages_path)
        updated_python_path = True

    try:
        # pylint:disable=import-outside-toplevel

        import spacy
        import spacy.util
        from spacy.language import Language
        from spacy.tokenizer import Tokenizer
        from spacy.tokens import Doc

        # pylint:enable=import-outside-toplevel
        # moves the modules and classes to global scope
        _spacy = spacy
        _spacy_utils = spacy.util
        _SpacyLanguage = Language
        _SpacyTokenizer = Tokenizer
        _SpacyDoc = Doc

        successful_import = True

    except ModuleNotFoundError:
        # spacy not installed
        pass


def get_installed_models() -> list[str]:
    if not successful_import:
        return []

    assert _spacy_utils is not None
    return [f"{model_name}" for model_name in _spacy_utils.get_installed_models()]


def _get_am_spacy_venv_python() -> str:
    if is_win:
        return os.path.join(_get_am_spacy_venv_path(), "Scripts", "python.exe")
    return os.path.join(_get_am_spacy_venv_path(), "bin", "python")


def _get_am_spacy_venv_path() -> str:
    python_version = f"{sys.version_info.major}_{sys.version_info.minor}"
    return os.path.join(mw.pm.addonFolder(), f"spacy-venv-python-{python_version}")


def create_spacy_venv() -> None:
    """
    We create a dedicated venv to avoid polluting the anki launcher environment
    """

    spacy_venv_path = _get_am_spacy_venv_path()

    # delete in case it already exists from previously failed attempts
    shutil.rmtree(spacy_venv_path, ignore_errors=True)

    python_path: str | None = venv_binary("python")

    if python_path is None:
        raise ValueError(
            "Anki API error. Install Anki from the official website to avoid this issue."
        )

    subprocess.run([python_path, "-m", "venv", spacy_venv_path], check=True)

    if is_win:
        spacy_venv_python = os.path.join(spacy_venv_path, "Scripts", "python.exe")
    else:
        spacy_venv_python = os.path.join(spacy_venv_path, "bin", "python")

    # make sure pip, setuptools, and wheel are up-to-date
    subprocess.run(
        [
            spacy_venv_python,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        check=True,
    )

    # six is necessary for some models
    subprocess.run(
        [spacy_venv_python, "-m", "pip", "install", "--upgrade", "spacy", "six"],
        check=True,
    )


def delete_spacy_venv() -> None:
    spacy_venv_path = _get_am_spacy_venv_path()
    try:
        shutil.rmtree(spacy_venv_path)
    except PermissionError:
        # windows does not like deleting files in use, so we add this flag file,
        # and we delete the venv on startup if the file exists
        (Path(spacy_venv_path) / ".delete_me").touch()


def maybe_delete_spacy_venv() -> None:
    # gracefully delete spacy venv on windows
    spacy_venv_path = _get_am_spacy_venv_path()
    flag = Path(spacy_venv_path, ".delete_me")
    if flag.exists():
        shutil.rmtree(spacy_venv_path)


def install_model(model_name: str) -> None:
    assert successful_import
    assert _spacy is not None

    subprocess.run(
        [_get_am_spacy_venv_python(), "-m", "spacy", "download", model_name], check=True
    )


def uninstall_model(model_name: str) -> None:
    assert successful_import
    assert _spacy is not None

    # the -y flag prevents a confirmation prompt
    subprocess.run(
        [_get_am_spacy_venv_python(), "-m", "pip", "uninstall", "-y", model_name],
        check=True,
    )


# the cache needs to have a max size to maintain garbage collection
@functools.lru_cache(maxsize=131072)
def get_nlp(spacy_model_name: str):  # type: ignore[no-untyped-def] # pylint:disable=too-many-branches, too-many-statements
    # -> Optional[spacy.Language]

    if not successful_import:
        return None

    assert _spacy is not None

    ################################################################
    #                       DISABLING PIPES
    ################################################################
    # Pipes add processing time, which means we want to disable as
    # many as possible for efficiency reasons.
    # We disable any pipes that are not necessary for producing
    # lemmas and pos (part of speech).
    # More info:
    # https://spacy.io/usage/processing-pipelines#disabling
    # https://spacy.io/models#design-modify
    ################################################################

    # dev_all_pipes: set[str] = {
    #     "tok2vec",
    #     "tagger",
    #     "morphologizer",
    #     "parser",
    #     "lemmatizer",
    #     "senter",
    #     "attribute_ruler",
    #     "ner",
    # }

    nlp = _spacy.load(spacy_model_name)

    # Get the enabled pipes based on language, default to an empty set if not defined
    enabled_pipes = LANGUAGE_PIPE_CONFIGS.get(nlp.lang, set())

    # Disable all other pipes that are not explicitly enabled
    for pipe in nlp.component_names:
        if pipe not in enabled_pipes:
            nlp.disable_pipe(pipe)

    ################################################################
    #                        CUSTOM PIPES
    ################################################################
    # The spacy models use 'pipes' that adjusts the output they produce.
    # These pipes are simply functions that take in the doc, makes
    # changes to it, and then returns it. This way the pipes sequentially
    # update the doc to make it more and more sophisticated.
    #
    # The korean and chinese models don't produce lemmas in the same
    # way as the other languages, so we have to make some custom
    # pipes to make them conform to the rest.
    #
    # We can then add the custom pipes to specific nlps this way:
    #     nlp.add_pipe("lemma_adder_chinese", last=True)
    #
    # The order of the pipes matters, so we add the pipe to the end
    # of the line to make sure that they do not cause problems for
    # any other pipes that might not be able to handle our doc changes.
    ################################################################
    @_SpacyLanguage.component("lemma_stripper_korean")  # type: ignore[misc]
    def lemma_stripper_korean(doc: _SpacyDoc) -> _SpacyDoc:
        # The korean lemmatizer produces lemmas in this format:
        #  누르+어
        # where the + parts are the conjugations.
        # We only want the stem, so we splice the string there
        for w in doc:
            conjugation_position = w.lemma_.find("+")
            if conjugation_position != -1:
                w.lemma_ = w.lemma_[:conjugation_position]
        return doc

    @_SpacyLanguage.component("lemma_adder_chinese")  # type: ignore[misc]
    def lemma_adder_chinese(doc: _SpacyDoc) -> _SpacyDoc:
        # The chinese models don't produce lemmas, so we just set them to be the text
        for w in doc:
            w.lemma_ = w.text
        return doc

    if nlp.lang == "zh":
        nlp.add_pipe("lemma_adder_chinese", last=True)

    if nlp.lang == "ko":
        nlp.add_pipe("lemma_stripper_korean", last=True)

    # print(f"pipe names: {nlp.pipe_names}")
    # print(f"pipe disabled: {nlp.disabled}")
    # print(f"component_names: {nlp.component_names}")
    # print(f"pipe names: {nlp.meta}")

    return nlp
