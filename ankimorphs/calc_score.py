from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .morpheme import Morpheme

# Anki stores the 'due' value of cards as a 32-bit integer
# on the backend, with '2147483647' being the max value before
# overflow. To prevent overflow when cards are repositioned,
# we decrement the second digit (from the left) of the max value,
# which should give plenty of leeway (10^8).
_DEFAULT_SCORE: int = 2047483647


####################################################################################
#                                      ALGORITHM
####################################################################################
####################################################################################

# The algorithm is calculated with the following equation
#
#    score = (
#        usefulness_weight * usefulness_penalty
#        + ave_difficulty_weight * ave_difficulty_penalty
#        + num_morphs_weight * num_morphs_penalty
#        + num_learning_weight * num_learning_penalty
#    )

# Usefulness is measured by frequency of the unknown morph(s)
#    The Lower (more frequent) is more useful
# Difficulty is the average frequency of the morphs in the sentence
#    Lower (the average morph is more frequent) is considered easier
# Num morphs is the length of the sentence, measured by number of morphs
#    The user can specify the target range of number of morphs
#    The farther the length is from the target, the higher the penalty
# Num learning is the number of morphs that are in the learning state
#    (this is for reinforcement of new / difficult morphs)
#    The user can specify the target number of learning morphs
#    The farther the number of learning morphs is from the target, the higher the penalty

#######################################
# The following should be user selected
# Target length of sentences
target_num_morphs_low = 4
target_num_morphs_high = 6

# Target number of morphs in the "learning" state
target_num_learning = 1

# Weights for the different criteria
usefulness_weight = 10
ave_difficulty_weight = 1
num_learning_weight = 5
num_morphs_weight = 1


#######################################
def _get_length_penalty(num_morphs: int) -> int:
    if num_morphs < target_num_morphs_low:
        return target_num_morphs_low - num_morphs
    elif num_morphs > target_num_morphs_high:
        return num_morphs - target_num_morphs_high
    else:
        return 0


def _get_ave_difficulty_penalty(sentence_difficulty: int, length: int) -> int:
    return int(sentence_difficulty / length)


def _get_learning_penalty(num_learning_morphs: int) -> int:
    if num_learning_morphs == target_num_learning:
        return 0
    else:
        return abs(num_learning_morphs - target_num_learning)


def get_card_score_and_unknowns_and_learning_status(
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[Morpheme]],
    morph_priority: dict[str, int],
) -> tuple[int, list[Morpheme], bool]:

    morph_unknown_penalty: int = 1000000
    unknown_morphs: list[Morpheme] = []
    no_morph_priority_value = len(morph_priority) + 1
    has_learning_morph: bool = False

    try:
        card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return _DEFAULT_SCORE, unknown_morphs, has_learning_morph

    usefulness_penalty = 0
    num_learning_morphs = 0
    sentence_difficulty = 0

    for morph in card_morphs:
        assert morph.highest_learning_interval is not None

        if morph.highest_learning_interval == 0:
            unknown_morphs.append(morph)
            if morph.lemma_and_inflection in morph_priority:
                usefulness_penalty += morph_priority[morph.lemma_and_inflection]
            else:
                usefulness_penalty += no_morph_priority_value

        elif morph.highest_learning_interval <= am_config.recalc_interval_for_known:
            has_learning_morph = True
            num_learning_morphs += 1

        if morph.lemma_and_inflection not in morph_priority:
            # Heavily penalizes if a morph is not in frequency file
            sentence_difficulty = no_morph_priority_value
        else:
            sentence_difficulty += morph_priority[morph.lemma_and_inflection]

    if len(unknown_morphs) == 0 and am_config.recalc_move_known_new_cards_to_the_end:
        # Move stale cards to the end of the queue
        return _DEFAULT_SCORE, unknown_morphs, has_learning_morph

    ##
    # Num learning penalty
    num_learning_penalty = _get_learning_penalty(num_learning_morphs)

    # Num morphs penalty
    num_morphs_penalty = _get_length_penalty(len(card_morphs))

    ave_difficulty_penalty = _get_ave_difficulty_penalty(
        sentence_difficulty, len(card_morphs)
    )

    ## Calculate the score
    score = (
        usefulness_weight * usefulness_penalty
        + ave_difficulty_weight * ave_difficulty_penalty
        + num_learning_weight * num_learning_penalty
        + num_morphs_weight * num_morphs_penalty
    )

    if score >= morph_unknown_penalty:
        # Cap morph priority penalties as described in #(2.2)
        score = morph_unknown_penalty - 1

    score += len(unknown_morphs) * morph_unknown_penalty

    # cap score to prevent 32-bit integer overflow
    score = min(score, _DEFAULT_SCORE)

    return score, unknown_morphs, has_learning_morph
