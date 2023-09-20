# -*- coding: utf-8 -*-
import gzip
import pickle as pickle
from functools import partial

from aqt.utils import tooltip

from .util import mw
from .preferences import get_preference as cfg
from .morphemes import MorphDb
from .exceptions import ProfileNotYetLoadedException


def get_stat_path(): return cfg('path_stats')


def load_stats():
    try:
        f = gzip.open(get_stat_path())
        d = pickle.load(f)
        f.close()
        return d
    except IOError:  # file DNE => create it
        return update_stats()
    except ProfileNotYetLoadedException:  # profile not loaded yet, can't do anything but wait
        return None


def save_stats(d):
    f = gzip.open(get_stat_path(), 'wb')
    pickle.dump(d, f, -1)
    f.close()


def update_stats(known_db=None):
    mw.taskman.run_on_main(partial(mw.progress.start, label='Updating stats', immediate=True))

    # Load known.db and get total morphemes known
    if known_db is None:
        known_db = MorphDb(cfg('path_known'), ignoreErrors=True)

    d = {'totalVariations': len(known_db.db), 'totalKnown': len(known_db.groups)}

    save_stats(d)
    mw.taskman.run_on_main(mw.progress.finish)
    return d


def get_unique_morph_toolbar_stats():
    d = load_stats()
    if not d:
        return 'U ???', '???'

    unique_morphs = d.get('totalKnown', 0)

    name = f'U: {unique_morphs}'
    details = 'U = Known Unique Morphs'
    return name, details


def get_all_morph_toolbar_stats():
    d = load_stats()
    if not d:
        return 'A ????', '???'

    unique_morphs = d.get('totalKnown', 0)
    all_morphs = d.get('totalVariations', unique_morphs)

    name = f'A: {all_morphs}'
    details = 'A = All Known Morphs'
    return name, details


def on_morph_stats_clicked():
    tooltip("U = Known Unique Morphs<br>A = All Known Morphs")
