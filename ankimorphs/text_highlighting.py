import re
from typing import Optional

from . import text_preprocessing
from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme


class SpanElement:

    def __init__(
        self, morph_group: str, morph_status: str, start_index: int, end_index: int
    ):
        # it's crucial that the morph_group parameter originates from Match[str].group()
        # because that maintains the original letter casing, which we want to preserve
        # in the highlighted version of the text.
        self.morph_group: str = morph_group
        self.morph_status: str = morph_status
        self.start_index: int = start_index
        self.end_index: int = end_index


def get_highlighted_text(
    am_config: AnkiMorphsConfig,
    card_morphs: list[Morpheme],
    text_to_highlight: str,
) -> str:
    # To highlight morphs based on their learning status, we wrap them in html span elements.
    # The problem with this approach is that injecting html between morphs can break the functionality
    # of ruby characters (https://docs.ankiweb.net/templates/fields.html#ruby-characters).
    #
    # To prevent that problem, we have to first have to iterate over the string and extract the ruby characters
    # and return the filtered string. Next, we can run almost the same procedure with the found morphs: extract
    # them and filter the string. Once both of these passes are completed, we are left with a string that
    # only has non-word characters and text that did not match any morphs.
    #
    # Take, for example, the following (contrived) text:
    #   "Hello[ハロー] myy world!"
    #
    # The process would look like this:
    # 1. The "[ハロー]" part is found to be ruby characters and is therefore removed from the
    # string and stored in a dict along with its original position, leaving us with string:
    #   "Hello myy world!"
    #
    # 2. The words "Hello" and "world" are found to be morphs, and information about them and their original position
    # are stored as SpanElement objects in a list, and are then removed from the string and replaced
    # by whitespaces, leaving us with:
    #   "      myy      !"
    #
    # 3. We now have all the information we need to reassemble the string with the span elements that contain the morphs
    # and any ruby characters that directly followed them will be included in the spans.
    #
    # The final highlighted string could end up looking something like this:
    #   "<span morph-status="known">Hello[ハロー]</span> myy <span morph-status="unknown">world</span>!"

    # print(f"text_to_highlight: {text_to_highlight}")
    # print(f"text_to_highlight list: {list(text_to_highlight)}")

    ruby_character_dict, text_to_highlight = _extract_ruby_characters_and_filter_string(
        am_config, text_to_highlight
    )
    span_elements, text_to_highlight = _extract_span_elements_and_filter_string(
        am_config, card_morphs, text_to_highlight
    )
    # sorting the spans allows for iteration by a single index instead of looping
    # through the list every time we want to find an element
    span_elements.sort(key=lambda span: span.start_index)

    # the string has now been sufficiently stripped and split into its constituent parts,
    # and we can now reassemble it
    highlighted_text_list: list[str] = []
    index: int = 0
    previous_span_index: int = -1

    while index < len(text_to_highlight):

        span_element: Optional[SpanElement] = _get_span_element(
            span_elements, previous_span_index
        )
        if (
            span_element is not None
            and span_element.start_index <= index < span_element.end_index
        ):
            span_string = span_element.morph_group

            if len(ruby_character_dict) > 0:
                # we need to do this in reverse order to preserve the indices
                global_string_index = span_element.end_index
                # this substring index is offset by +1 because it is used for string splicing
                sub_string_index = len(span_string)

                while global_string_index > span_element.start_index:
                    if global_string_index in ruby_character_dict:
                        span_string = (
                            span_string[:sub_string_index]
                            + ruby_character_dict[global_string_index]
                            + span_string[sub_string_index:]
                        )
                        # this entry is not needed anymore
                        del ruby_character_dict[global_string_index]

                    global_string_index -= 1
                    sub_string_index -= 1

            span_string = (
                f'<span morph-status="{span_element.morph_status}">{span_string}</span>'
            )
            highlighted_text_list.append(span_string)
            index = span_element.end_index

            # keep the index within range
            if previous_span_index < len(span_elements) - 2:
                previous_span_index += 1

        else:
            non_span_string = text_to_highlight[index]
            if len(ruby_character_dict) > 0:
                # add any ruby characters found in the subsequent index.
                # note: it can seem unnecessarily complicated to append
                # the ruby character in this else branch, but since the
                # if branch above can potentially also trigger on the
                # subsequent index _and_ that takes priority, it means that
                # this next ruby character might never be reached unless
                # we do it here.
                next_index = index + 1
                if next_index in ruby_character_dict:
                    non_span_string += ruby_character_dict[next_index]
                    # this entry is not needed anymore
                    del ruby_character_dict[next_index]

            highlighted_text_list.append(non_span_string)
            index += 1

    # print(f'highlighted text: {"".join(highlighted_text_list)}')
    return "".join(highlighted_text_list)


def _extract_ruby_characters_and_filter_string(
    am_config: AnkiMorphsConfig, text_to_highlight: str
) -> tuple[dict[int, str], str]:
    ruby_character_dict: dict[int, str] = {}

    # most users probably don't have ruby characters on their cards,
    # so we only want to do all this extra work of extracting and replacing
    # if they have activated the relevant pre-process option
    if not am_config.preprocess_ignore_bracket_contents:
        return ruby_character_dict, text_to_highlight

    while True:
        # matches first found, left to right
        match: Optional[re.Match[str]] = re.search(
            text_preprocessing.square_brackets_regex, text_to_highlight
        )
        if match is None:
            break

        ruby_character_dict[match.start()] = match.group()

        # remove the found match from the string and repeat
        text_to_highlight = (
            text_to_highlight[: match.start()] + text_to_highlight[match.end() :]
        )

    return ruby_character_dict, text_to_highlight


def _extract_span_elements_and_filter_string(
    am_config: AnkiMorphsConfig, card_morphs: list[Morpheme], text_to_highlight: str
) -> tuple[list[SpanElement], str]:
    span_elements: list[SpanElement] = []

    # To avoid formatting a smaller morph contained in a bigger morph, we reverse sort
    # the morphs based on length and extract those first.
    morphs_by_size = sorted(
        card_morphs,
        key=lambda _simple_morph: len(_simple_morph.inflection),
        reverse=True,
    )

    for morph in morphs_by_size:
        # print(f"morph: {morph.lemma}, {morph.inflection}")
        assert morph.highest_learning_interval is not None

        if morph.highest_learning_interval == 0:
            morph_status = "unknown"
        elif morph.highest_learning_interval < am_config.recalc_interval_for_known:
            morph_status = "learning"
        else:
            morph_status = "known"

        # escaping special regex characters is crucial because morphs from malformed text
        # sometimes can include them, e.g. "?몇"
        regex_pattern: str = f"{re.escape(morph.inflection)}"
        morph_matches = re.finditer(
            regex_pattern, text_to_highlight, flags=re.IGNORECASE
        )

        for morph_match in morph_matches:
            start_index = morph_match.start()
            end_index = morph_match.end()
            morph_len = end_index - start_index

            # the morph_match.group() maintains the original letter casing of the
            # morph found in the text, which is crucial because we want everything
            # to be identical to the original text.
            span_elements.append(
                SpanElement(morph_match.group(), morph_status, start_index, end_index)
            )

            # we need to preserve indices, so we replace the morphs with whitespaces
            text_to_highlight = (
                text_to_highlight[:start_index]
                + "".join([" " for _ in range(morph_len)])
                + text_to_highlight[end_index:]
            )

    return span_elements, text_to_highlight


def _get_span_element(
    span_elements: list[SpanElement], previous_span_index: int
) -> Optional[SpanElement]:
    try:
        return span_elements[previous_span_index + 1]
    except IndexError:
        # This exception should only happen when the span_elements
        # list is empty, which should be a rare occurrence. Catching
        # a rare exception is more efficient than checking with an
        # if statement every time.
        return None
