def get_nlp(spacy_model_name: str):  # type: ignore[no-untyped-def] # pylint:disable=too-many-branches, too-many-statements
    # -> Optional[spacy.Language]
    try:
        import spacy  # pylint:disable=import-outside-toplevel
        from spacy.lang.char_classes import (  # pylint:disable=import-outside-toplevel
            LIST_ELLIPSES,
            LIST_ICONS,
        )
        from spacy.language import Language  # pylint:disable=import-outside-toplevel
        from spacy.tokenizer import Tokenizer  # pylint:disable=import-outside-toplevel
        from spacy.tokens import Doc  # pylint:disable=import-outside-toplevel
        from spacy.util import (  # pylint:disable=import-outside-toplevel
            compile_infix_regex,
        )
    except ModuleNotFoundError:
        # spacy not installed
        return None

    ################################################################
    #                           INFIXES
    ################################################################
    # The infixes rules tell the tokenizer where to split the text
    # segments. We want to split on everything that is not alphanum (\w),
    # hyphen (-), and apostrophes ('), french: (’)
    # Since the text can be malformed, e.g. "los?«Harry", we have to split
    # before AND after the non-alpha characters.
    # If you only split before, then you get: los ? «Harry
    # if you only split after: los? « Harry
    # if you do both: lost ? « Harry
    #
    # Regex explanation:
    # ?! <- This means inverse match, i.e., don't match
    # (?! [...]) <- this means lookahead and inverse match anything inside the brackets
    # (?<! [...]) <- this means lookbehind and inverse match anything inside the brackets
    ################################################################
    infixes = (
        LIST_ELLIPSES
        + LIST_ICONS
        + [
            r"(?<![\w\-\'\’])",
            r"(?![\w\-\'\’])",
        ]
    )
    infix_re = compile_infix_regex(infixes)

    ################################################################
    #                        CUSTOM PIPES
    ################################################################
    # The spacy models use 'pipes' that adjusts the output they produce.
    # These pipes are simply functions that take in the doc, makes changes
    # to it, and then returns it. This way the pipes sequentially
    # update the doc to make it more and more sophisticated.
    #
    # The korean and chinese models don't produce lemmas in the same
    # way as the other languages, so we therefore have to make some
    # custom pipes to make them conform to the rest.
    # We can then add the custom pipes to specific nlps this way:
    #     nlp.add_pipe("chinese_lemma_adder", last=True)
    # The order of the pipes matters, so we add the pipe to the end
    # of the line to make sure the docs have been given the necessary
    # changes already, and to not cause problems for any earlier pipes
    # that might expect the docs to be different compared to our changes.
    ################################################################
    @Language.component("strip_korean_lemmas")
    def strip_korean_lemmas(doc: Doc) -> Doc:
        # The korean lemmatizer produces lemmas in this format:
        #  누르+어
        # where the + parts are the conjugations.
        # We only want the stem, so we splice the string there
        for w in doc:
            conjugation_position = w.lemma_.find("+")
            if conjugation_position != -1:
                w.lemma_ = w.lemma_[:conjugation_position]
        return doc

    @Language.component("chinese_lemma_adder")
    def stripped_korean_lemma(doc: Doc) -> Doc:
        # The chinese models don't produce lemmas, so we just set them to be the text
        for w in doc:
            w.lemma_ = w.text
        return doc

    ################################################################
    #                       DISABLING PIPES
    ################################################################
    # Pipes add processing time, that means we want to disable as
    # many as possible for efficiency reasons.
    # We disable any pipes that are not necessary for producing
    # lemmas and pos (part of speech).
    # More info:
    # https://spacy.io/usage/processing-pipelines#disabling
    # https://spacy.io/models#design-modify
    ################################################################
    enabled_pipes: set[str] = {""}
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

    nlp = spacy.load(spacy_model_name)

    if nlp.lang == "ja":
        enabled_pipes = {""}
    elif nlp.lang == "nb":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "attribute_ruler",
            "lemmatizer",
            "morphologizer",
            "ner",
        }
    elif nlp.lang == "da":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "morphologizer",
            "lemmatizer",
        }
    elif nlp.lang == "de":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "fr":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "en":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "tagger",
            "attribute_ruler",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "es":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "sv":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "nl":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "hr":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "fi":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "el":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "it":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "lt":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "mk":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "pl":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "pt":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "ro":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "tagger",
            "morphologizer",
            "lemmatizer",
            "attribute_ruler",
        }
    elif nlp.lang == "sl":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "lemmatizer",
            "morphologizer",
        }
    elif nlp.lang == "ca":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.tokenizer.infix_finditer = infix_re.finditer
        enabled_pipes = {
            "tok2vec",
            "morphologizer",
            "lemmatizer",
        }
    elif nlp.lang == "ru":
        assert isinstance(nlp.tokenizer, Tokenizer)
        enabled_pipes = {
            "tok2vec",
            "morphologizer",
            "lemmatizer",
        }
    elif nlp.lang == "uk":
        assert isinstance(nlp.tokenizer, Tokenizer)
        enabled_pipes = {
            "tok2vec",
            "morphologizer",
            "lemmatizer",
        }
    elif nlp.lang == "ko":
        assert isinstance(nlp.tokenizer, Tokenizer)
        nlp.add_pipe("strip_korean_lemmas", last=True)
        enabled_pipes = {
            "tok2vec",
            "morphologizer",
            "lemmatizer",
            "strip_korean_lemmas",
        }
    elif nlp.lang == "zh":
        nlp.add_pipe("chinese_lemma_adder", last=True)
        enabled_pipes = {
            "tok2vec",
            "tagger",
            "attribute_ruler",
            "chinese_lemma_adder",
        }

    for pipe in nlp.component_names:
        if pipe not in enabled_pipes:
            nlp.disable_pipe(pipe)

    # print(f"pipe names: {nlp.pipe_names}")
    # print(f"pipe disabled: {nlp.disabled}")
    # print(f"component_names: {nlp.component_names}")
    # print(f"pipe names: {nlp.meta}")

    return nlp


def get_installed_models() -> list[str]:
    try:
        import spacy.util  # pylint:disable=import-outside-toplevel

        return [f"{model_name}" for model_name in spacy.util.get_installed_models()]
    except ModuleNotFoundError:
        # spacy not installed
        return []
