from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme

# Anki stores the 'due' value of cards as a 32-bit integer
# on the backend, with '2147483647' being the max value before
# overflow. To prevent overflow when cards are repositioned,
# we decrement the second digit (from the left) of the max value,
# which should give plenty of leeway (10^8).
_DEFAULT_SCORE: int = 2_047_483_647


####################################################################################
#                                      ALGORITHM
####################################################################################
####################################################################################

# The algorithm is calculated with the following equation
#
#    score = (
#        TOTAL_PRIORITY_FOR_UNKNOWN_WEIGHT * total_priority_for_unknown
#        + AVG_PRIORITY_WEIGHT * avg_priority
#        + LEARNING_MORPHS_DISTANCE_WEIGHT * (learning_morphs_distance**2)
#        + ALL_MORPHS_DISTANCE_WEIGHT * (all_morphs_distance**2)
#    )
#
# Each of the factors has a weight (in CAPITALS) which determines
#    how much that factor contributes to the final score.
# A lower total score means that the card will show up sooner 
#    in the new card list, so each of the factors can be thought
#    of as a penalty.
#
# Priority is measured by frequency of the morph
#    An unknown morph that has a higher frequency will have a lower
#    priority score
#
# total_priority_for_unknown is the sum of the priority scores for
#    all of the unknown morphs
#
# avg_priority is the sum of the priority scores for all of the
#    known and learning scores
#
# learning_morphs_distance is the number of morphs that are in the learning state
#    (this is for reinforcement of new / difficult morphs)
#    The user can specify the target number of learning morphs
#    The farther the number of learning morphs is from the target, the higher the penalty
#
# all_morphs_distance is how much shorter/longer the {read field
#    / parse field / input field} is than the desired length range
#    (measured in the number of morphs)


#######################################
# The following should be user selected
# Target length of sentences
TARGET_NUM_MORPHS_LOW = 4
TARGET_NUM_MORPHS_HIGH = 6

# Target number of morphs in the "learning" state
TARGET_NUM_LEARNING = 1

# Weights for the different criteria
TOTAL_PRIORITY_FOR_UNKNOWN_WEIGHT = 10
AVG_PRIORITY_WEIGHT = 1
LEARNING_MORPHS_DISTANCE_WEIGHT = 5
ALL_MORPHS_DISTANCE_WEIGHT = 1


#######################################
def _get_distance_from_morphs_length_target(num_morphs: int) -> int:
    if num_morphs < TARGET_NUM_MORPHS_LOW:
        return TARGET_NUM_MORPHS_LOW - num_morphs
    if num_morphs > TARGET_NUM_MORPHS_HIGH:
        return num_morphs - TARGET_NUM_MORPHS_HIGH
    return 0


def get_card_score_and_unknowns_and_learning_status(  # pylint:disable=too-many-locals
    am_config: AnkiMorphsConfig,
    card_id: int,
    card_morph_map_cache: dict[int, list[Morpheme]],
    morph_priority: dict[str, int],  # todo: maybe name it frequency instead?
) -> tuple[int, list[Morpheme], bool]:

    morph_unknown_penalty: int = 1_000_000
    unknown_morphs: list[Morpheme] = []
    no_morph_priority_value = len(morph_priority) + 1
    has_learning_morph: bool = False

    try:
        card_morphs: list[Morpheme] = card_morph_map_cache[card_id]
    except KeyError:
        # card does not have morphs or is buggy in some way
        return _DEFAULT_SCORE, unknown_morphs, has_learning_morph

    total_priority_for_unknown = 0
    num_learning_morphs = 0
    total_priority = 0

    for morph in card_morphs:
        assert morph.highest_learning_interval is not None

        if morph.highest_learning_interval == 0:
            unknown_morphs.append(morph)
            if morph.lemma_and_inflection in morph_priority:
                total_priority_for_unknown += morph_priority[morph.lemma_and_inflection]
            else:
                total_priority_for_unknown += no_morph_priority_value

        elif morph.highest_learning_interval < am_config.recalc_interval_for_known:
            has_learning_morph = True
            num_learning_morphs += 1

        if morph.lemma_and_inflection not in morph_priority:
            # Heavily penalizes if a morph is not in frequency file
            total_priority = no_morph_priority_value
        else:
            total_priority += morph_priority[morph.lemma_and_inflection]

    if len(unknown_morphs) == 0 and am_config.recalc_move_known_new_cards_to_the_end:
        # Move stale cards to the end of the queue
        return _DEFAULT_SCORE, unknown_morphs, has_learning_morph

    learning_morphs_distance = abs(num_learning_morphs - TARGET_NUM_LEARNING)
    all_morphs_distance = _get_distance_from_morphs_length_target(len(card_morphs))
    avg_priority = int(total_priority / len(card_morphs))

    score = (
        TOTAL_PRIORITY_FOR_UNKNOWN_WEIGHT * total_priority_for_unknown
        + AVG_PRIORITY_WEIGHT * avg_priority
        + LEARNING_MORPHS_DISTANCE_WEIGHT * (learning_morphs_distance**2)
        + ALL_MORPHS_DISTANCE_WEIGHT * (all_morphs_distance**2)
    )

    if score >= morph_unknown_penalty:
        # Cap morph priority penalties as described in #(2.2)
        score = morph_unknown_penalty - 1

    score += len(unknown_morphs) * morph_unknown_penalty

    # cap score to prevent 32-bit integer overflow
    score = min(score, _DEFAULT_SCORE)

    print(f"card id: {card_id}")
    print(f"card_morphs: {[morph.inflection for morph in card_morphs]}")
    print(f"unknown_morphs: {len(unknown_morphs)}")
    print(f"num_learning_penalty: {learning_morphs_distance}")
    print(f"num_morphs_penalty: {all_morphs_distance}")
    print(f"ave_difficulty_penalty: {avg_priority}")
    print(f"score: {score}")
    print()

    return score, unknown_morphs, has_learning_morph
