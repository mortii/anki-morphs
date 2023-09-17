import os


class FakeConfig:
    def __init__(self):
        self.default = {
            'path_all': os.path.join(os.getcwd(), 'tests', 'data', 'dbs', 'all.db'),
            'path_seen': os.path.join(os.getcwd(), 'tests', 'data', 'dbs', 'seen.db'),
            'path_known': os.path.join(os.getcwd(), 'tests', 'data', 'dbs', 'known.db'),
            'path_mature': os.path.join(os.getcwd(), 'tests', 'data', 'dbs', 'mature.db'),
            'path_frequency': os.path.join(os.getcwd(), 'tests', 'data', 'dbs', 'data/frequency.txt'),
            'path_stats': os.path.join(os.getcwd(), 'tests', 'data', 'dbs', 'morphman.stats'),
            'threshold_mature': 21,  # 21 days is what Anki uses
            'threshold_known': 10 / 86400.,
            'threshold_seen': 1 / 86400.,
            'text file import maturity': 22,
            'browse same focus key': 'l',
            'browse same focus key non vocab': 'Shift+l',
            'set known and skip key': 'k',
            'set batch play key': 'Ctrl+Alt+P',
            'set extract morphemes key': 'Ctrl+Alt+E',
            'set learn now key': 'Ctrl+Alt+N',
            'set mass tagger key': 'Ctrl+Alt+T',
            'set view morphemes key': 'Ctrl+Alt+V',
            'set bold unknowns key': 'Ctrl+Alt+B',
            'auto skip alternatives': True,
            'print number of alternatives skipped': True,
            'loadAllDb': True,
            'saveDbs': True,  # whether to save all.db, known.db, mature.db, and seen.db
            'saveSQLite': False,  # save the data also in an sqlite database
            'set due based on mmi': True,
            'ignore maturity': False,  # if True, pretends card maturity is always zero
            'batch media fields': ['Video', 'Sound'],
            'min good sentence length': 2,
            'max good sentence length': 30,
            'reinforce new vocab weight': 5.0,
            'verb bonus': 0,
            'priority.db weight': 200,
            'frequency.txt bonus': 100000,
            'no priority penalty': 1000000,
            'only update k+2 and below': False,
            'next new card feature': True,
            'new card merged fill': False,
            'new card merged fill min due': 100000}
        self.profile_overrides = {}
        self.model_overrides = {
            'JtMW': {'set due based on mmi': False, 'ignore maturity': True},
            'JSPfEC': {'set due based on mmi': False},
            'Tae Kim Cloze': {'set due based on mmi': False},
            'Yotsubato': {'set due based on mmi': True},
            'Rikaisama': {'set due based on mmi': False},
            'Kore': {'set due based on mmi': False}}
        self.deck_overrides = {
            'Sentences': {'new card merged fill': True},
            'Sentences::subs2srs': {'new card merged fill': True},
            'Sentences::vn2srs': {'new card merged fill': True},
            'ExtraVocab': {'new card merged fill': True},
            'ExtraVocab::_Yotsubato': {'new card merged fill': True},
            'ExtraVocab::_Kore': {'new card merged fill': True}}
