from __future__ import annotations

import copy
import csv
from pathlib import Path

from .. import ankimorphs_config
from .. import ankimorphs_globals as am_globals
from ..ankimorphs_db import AnkiMorphsDB
from ..morpheme import MorphOccurrence
from .progress_output_dialog import OutputOptions
from ..recalc.morph_priority_utils import _get_morph_priority


# We want a function that takes in bins (and maybe a config and db?)
# and returns a some sort of progress report.
# This function should load the database and the morph priorities, 
# bin them, then do a calculation

# thinking a bit more about architecture.
# Each ProgressReport has an associated bin_range AND config. 
# These can be added together as needed...

class Bins:
    """Stores bins for morph priority."""
    def __init__(
        self, indexes: list[int,int]
    ) -> None:

        # Lower index should be larger than upper index,
        # and both should be positive integers
        for bin_index in indexes:
            lower_index, upper_index = bin_index
            if lower_index < 1 or upper_index < lower_index:
                raise InvalidBinIndexException(bin_index)
        
        self.indexes = indexes


class ProgressReport:
    #__slots__ = ( # What are these?
    #    "unique_morphs",
    #    "unique_known",
    #    "unique_learning",
    #    "unique_unknowns",
    #    "total_morphs",
    #    "total_known",
    #    "total_learning",
    #    "total_unknowns",
    #)

    def __init__(
        self, min_priority: int, max_priority: int, 
        config_filter: AnkiMorphsConfigFilter
    ) -> None:
        
        if min_priority < 1 or max_priority < min_priority:
            raise InvalidBinIndexException()
        
        self.min_priority = min_priority
        self.max_priority = max_priority
        self.config_filter = config_filter

        # Ideally, these would be sets of Morphemes. However, I haven't
        # yet figured out if these objects are really available...
        self.unique_known: set[str] = set()
        self.unique_learning: set[str] = set()
        self.unique_unknowns: set[str] = set()

    def get_total_known(self) -> int:
        return len(self.unique_known)
    
    def get_total_learning(self) -> int:
        return len(self.unique_learning)
    
    def get_total_unknowns(self) -> int:
        return len(self.unique_unknowns)
    def get_total_morphs(self) -> int:
        return self.get_total_known() + self.get_total_learning() + \
               self.get_total_unknowns()


def _update_progress_report(
    progress_report: ProgressReport,
    morph: str,
    learning_status: str
) -> None:

    if learning_status == "unknown":
        progress_report.unique_unknowns.add(morph)
    elif learning_status == "learning":
        progress_report.unique_learning.add(morph)
    elif learning_status == "known":
        progress_report.unique_known.add(morph)
    else:
        raise  

# I may want to pass bins into this function?
def get_progress_reports(
        am_config: AnkiMorphsConfig, am_db: AnkiMorphsDB, bins: Bins 
) -> list[ProgressReport]:
    
    reports = []

    # To start, let's just calculate for all enabled filters.
    read_enabled_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_read_enabled_filters()
    )

    for config_filter in read_enabled_config_filters:

        morph_priorities: dict[str, int] = _get_morph_priority(
            am_db, am_config, config_filter
        )

        for min_priority, max_priority in bins.indexes:
            report = ProgressReport(min_priority,max_priority,config_filter)

            morph_status = am_db.get_morph_lemmas_learning_statuses()
            for morph in morph_status:
                key = morph + morph
                if key not in morph_priorities:
                    continue
                elif  morph_priorities[key] >= min_priority and \
                      morph_priorities[key] <= max_priority:
                    _update_progress_report(report, morph, morph_status[morph])
            reports.append(report)

    return reports










