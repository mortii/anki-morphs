################################################################
#                          IMPORTS
################################################################
# We have to use implicit imports from the 'ankimorphs'-module
# because ankiweb changes the directory name to a number instead
# of 'ankimorphs'
#
# Correct:
# from . import browser_utils
#
# Incorrect:
# from ankimorphs import browser_utils
################################################################

from functools import partial
from typing import Literal

import aqt
from anki.cards import Card
from anki.collection import OpChangesAfterUndo
from aqt import gui_hooks, mw
from aqt.browser.browser import Browser
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAction,
    QDesktopServices,
    QKeySequence,
    QMenu,
    QUrl,
)
from aqt.reviewer import Reviewer
from aqt.toolbar import Toolbar
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from . import (
    ankimorphs_globals,
    browser_utils,
    name_file_utils,
    recalc,
    reviewing_utils,
    settings_dialog,
    toolbar_stats,
)
from .ankimorphs_db import AnkiMorphsDB
from .config import AnkiMorphsConfig, AnkiMorphsConfigFilter, get_read_enabled_filters
from .frequency_file_generator import FrequencyFileGeneratorDialog
from .readability_report_generator import ReadabilityReportGeneratorDialog
from .settings_dialog import SettingsDialog
from .tag_selection_dialog import TagSelectionDialog
from .toolbar_stats import MorphToolbarStats

TOOL_MENU: str = "am_tool_menu"
BROWSE_MENU: str = "am_browse_menu"
CONTEXT_MENU: str = "am_context_menu"

startup_sync: bool = True


def main() -> None:
    # Support anki version 2.1.50 and above
    # Place hooks in the order they are executed

    gui_hooks.top_toolbar_did_init_links.append(init_toolbar_items)

    gui_hooks.profile_did_open.append(init_db)
    gui_hooks.profile_did_open.append(register_addon_dialogs)
    gui_hooks.profile_did_open.append(redraw_toolbar)
    gui_hooks.profile_did_open.append(init_tool_menu_and_actions)
    gui_hooks.profile_did_open.append(init_browser_menus_and_actions)
    gui_hooks.profile_did_open.append(replace_reviewer_functions)

    gui_hooks.sync_will_start.append(recalc_on_sync)

    gui_hooks.webview_will_show_context_menu.append(add_name_action)

    gui_hooks.reviewer_did_answer_card.append(insert_seen_morphs)

    gui_hooks.state_did_undo.append(rebuild_seen_morphs)

    gui_hooks.profile_will_close.append(clear_seen_morphs)


def init_toolbar_items(links: list[str], toolbar: Toolbar) -> None:
    # Adds the 'U: A:' and 'Recalc' to the toolbar

    morph_toolbar_stats = MorphToolbarStats()

    links.append(
        toolbar.create_link(
            cmd="recalc_toolbar",
            label="Recalc",
            func=recalc.recalc,
            tip="AnkiMorph Recalc",
            id="recalc_toolbar",
        )
    )
    links.append(
        toolbar.create_link(
            cmd="unique_morphs",
            label=morph_toolbar_stats.unique_morphs,
            func=lambda: tooltip("U = Known Unique Morphs<br>A = All Known Morphs"),
            tip="U = Known Unique Morphs",
            id="unique_morphs",
        )
    )
    links.append(
        toolbar.create_link(
            cmd="all_morphs",
            label=morph_toolbar_stats.all_morphs,
            func=lambda: tooltip("U = Known Unique Morphs<br>A = All Known Morphs"),
            tip="A = All Known Morphs",
            id="all_morphs",
        )
    )


def register_addon_dialogs() -> None:
    # We use the Anki dialog manager to handle our dialogs

    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.SETTINGS_DIALOG_NAME, creator=SettingsDialog
    )
    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.FREQUENCY_FILE_GENERATOR_DIALOG_NAME,
        creator=FrequencyFileGeneratorDialog,
    )
    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.READABILITY_REPORT_GENERATOR_DIALOG_NAME,
        creator=ReadabilityReportGeneratorDialog,
    )


def init_db() -> None:
    read_config_filters: list[AnkiMorphsConfigFilter] = get_read_enabled_filters()
    has_active_note_filter = False

    for config_filter in read_config_filters:
        if config_filter.note_type != "":
            has_active_note_filter = True

    am_db = AnkiMorphsDB()
    am_db.create_all_tables()

    if has_active_note_filter:
        AnkiMorphsDB.rebuild_seen_morphs_today()

    am_db.con.close()


def redraw_toolbar() -> None:
    # Updates the toolbar stats
    # wrapping this makes testing easier because we don't have to mock mw
    assert mw is not None
    mw.toolbar.draw()


def init_tool_menu_and_actions() -> None:
    assert mw is not None

    for action in mw.form.menuTools.actions():
        if action.objectName() == TOOL_MENU:
            return  # prevents duplicate menus on profile-switch

    am_config = AnkiMorphsConfig()

    settings_action = create_settings_action(am_config)
    recalc_action = create_recalc_action(am_config)
    frequency_list_action = create_frequency_file_action(am_config)
    readability_report_action = create_readability_report_action(am_config)
    guide_action = create_guide_action()
    changelog_action = create_changelog_action()

    am_tool_menu = create_am_tool_menu()
    am_tool_menu.addAction(settings_action)
    am_tool_menu.addAction(recalc_action)
    am_tool_menu.addAction(frequency_list_action)
    am_tool_menu.addAction(readability_report_action)
    am_tool_menu.addAction(guide_action)
    am_tool_menu.addAction(changelog_action)

    if ankimorphs_globals.DEV_MODE:
        test_action = create_test_action()
        am_tool_menu.addAction(test_action)


def init_browser_menus_and_actions() -> None:
    am_config = AnkiMorphsConfig()

    view_action = create_view_morphs_action(am_config)
    learn_now_action = create_learn_now_action(am_config)
    browse_morph_action = create_browse_same_morph_action()
    browse_morph_unknowns_action = create_browse_same_morph_unknowns_action(am_config)
    already_known_tagger_action = create_already_known_tagger_action(am_config)

    def setup_browser_menu(_browser: Browser) -> None:
        browser_utils.browser = _browser

        for action in browser_utils.browser.form.menubar.actions():
            if action.objectName() == BROWSE_MENU:
                return  # prevents duplicate menus on profile-switch

        am_browse_menu = QMenu("AnkiMorphs", mw)
        am_browse_menu_creation_action = browser_utils.browser.form.menubar.addMenu(
            am_browse_menu
        )
        assert am_browse_menu_creation_action is not None
        am_browse_menu_creation_action.setObjectName(BROWSE_MENU)
        am_browse_menu.addAction(view_action)
        am_browse_menu.addAction(learn_now_action)
        am_browse_menu.addAction(browse_morph_action)
        am_browse_menu.addAction(browse_morph_unknowns_action)
        am_browse_menu.addAction(already_known_tagger_action)

    def setup_context_menu(_browser: Browser, context_menu: QMenu) -> None:
        for action in context_menu.actions():
            if action.objectName() == CONTEXT_MENU:
                return  # prevents duplicate menus on profile-switch

        context_menu_creation_action = context_menu.insertSeparator(learn_now_action)
        assert context_menu_creation_action is not None
        context_menu.addAction(view_action)
        context_menu.addAction(learn_now_action)
        context_menu.addAction(browse_morph_action)
        context_menu.addAction(browse_morph_unknowns_action)
        context_menu.addAction(already_known_tagger_action)
        context_menu_creation_action.setObjectName(CONTEXT_MENU)

    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
    gui_hooks.browser_will_show_context_menu.append(setup_context_menu)


def recalc_on_sync() -> None:
    # Sync automatically happens on Anki startup, so we have
    # to check for that before we run recalc
    global startup_sync

    if startup_sync:
        startup_sync = False
    else:
        am_config = AnkiMorphsConfig()
        if am_config.recalc_on_sync:
            recalc.recalc()


def replace_reviewer_functions() -> None:
    assert mw is not None

    mw.reviewer.nextCard = reviewing_utils.am_next_card

    mw.reviewer._shortcutKeys = partial(
        reviewing_utils.am_reviewer_shortcut_keys,
        self=mw.reviewer,
        _old=Reviewer._shortcutKeys,
    )


def insert_seen_morphs(
    reviewer: Reviewer, card: Card, ease: Literal[1, 2, 3, 4]
) -> None:
    del reviewer, ease  # unused
    am_db = AnkiMorphsDB()
    am_db.update_seen_morphs_today_single_card(card.id)
    am_db.con.close()


def rebuild_seen_morphs(changes: OpChangesAfterUndo) -> None:
    ################################################################
    #                      TRACKING SEEN MORPHS
    ################################################################
    # We need to keep track of which morphs have been seen today,
    # which gets complicated when a user undos or redos cards.
    #
    # When a card is answered/set known, we insert all the card's
    # morphs into the 'Seen_Morphs'-table, if a morph is already
    # in the table, we just ignore the insert error. This makes
    # it tricky to remove morphs from the table  when undo is used
    # because we don't track if the morphs were already in the table
    # or not. To not have to deal with this removal problem, we just
    # drop the entire table and rebuild it with the morphs of all
    # the studied cards. This is admittedly costly, but it only
    # happens on 'undo,' which should be a rare occurrence.
    #
    # REDO:
    # Redoing, i.e., undoing an undo (Ctrl+Shift+Z), is almost
    # impossible to distinguish from a regular forward operation.
    # Since this is such a nightmare to deal with, and is hopefully
    # a rare occurrence, this will just be left as unexpected behavior.
    # Whatever bugs the user might experience at that point is not a
    # concern.
    ################################################################
    del changes  # unused

    AnkiMorphsDB.rebuild_seen_morphs_today()

    if ankimorphs_globals.DEV_MODE:
        print("Seen_Morphs:")
        am_db = AnkiMorphsDB()
        am_db.print_table("Seen_Morphs")
        am_db.con.close()


def clear_seen_morphs() -> None:
    AnkiMorphsDB.drop_seen_morphs_table()


def create_am_tool_menu() -> QMenu:
    assert mw is not None
    am_tool_menu = QMenu("AnkiMorphs", mw)
    am_tool_menu_creation_action = mw.form.menuTools.addMenu(am_tool_menu)
    assert am_tool_menu_creation_action is not None
    am_tool_menu_creation_action.setObjectName(TOOL_MENU)
    return am_tool_menu


def create_recalc_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Recalc", mw)
    action.setShortcut(am_config.shortcut_recalc)
    action.triggered.connect(recalc.recalc)
    return action


def create_settings_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Settings", mw)
    action.setShortcut(am_config.shortcut_settings)
    action.triggered.connect(
        partial(aqt.dialogs.open, name=ankimorphs_globals.SETTINGS_DIALOG_NAME)
    )
    return action


def create_guide_action() -> QAction:
    desktop_service = QDesktopServices()
    action = QAction("&Guide (web)", mw)
    action.triggered.connect(
        lambda: desktop_service.openUrl(
            QUrl("https://mortii.github.io/anki-morphs/user_guide/intro.html")
        )
    )
    return action


def create_changelog_action() -> QAction:
    desktop_service = QDesktopServices()
    action = QAction("&Changelog (web)", mw)
    action.triggered.connect(
        lambda: desktop_service.openUrl(
            QUrl("https://github.com/mortii/anki-morphs/releases")
        )
    )
    return action


def create_learn_now_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Learn Card Now", mw)
    action.setShortcut(am_config.shortcut_learn_now)
    action.triggered.connect(browser_utils.run_learn_card_now)
    return action


def create_browse_same_morph_action() -> QAction:
    action = QAction("&Browse Same Morphs", mw)
    action.triggered.connect(browser_utils.run_browse_morph)
    return action


def create_browse_same_morph_unknowns_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Browse Same Unknown Morphs", mw)
    action.setShortcut(am_config.shortcut_browse_ready_same_unknown)
    action.triggered.connect(
        partial(browser_utils.run_browse_morph, search_unknowns=True)
    )
    return action


def create_view_morphs_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&View Morphemes", mw)
    action.setShortcut(am_config.shortcut_view_morphemes)
    action.triggered.connect(browser_utils.run_view_morphs)
    return action


def create_already_known_tagger_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Tag As Known", mw)
    action.setShortcut(am_config.shortcut_set_known_and_skip)
    action.triggered.connect(browser_utils.run_already_known_tagger)
    return action


def add_name_action(web_view: AnkiWebView, menu: QMenu) -> None:
    assert mw is not None
    selected_text = web_view.selectedText()
    if selected_text == "":
        return
    action = QAction("Mark as name", menu)
    action.triggered.connect(lambda: name_file_utils.add_name_to_file(selected_text))
    action.triggered.connect(AnkiMorphsDB.insert_names_to_seen_morphs)
    action.triggered.connect(mw.reviewer.bury_current_card)
    menu.addAction(action)


def create_frequency_file_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Frequency File Generator", mw)
    action.setShortcut(am_config.shortcut_frequency_file_generator)
    action.triggered.connect(
        partial(
            aqt.dialogs.open,
            name=ankimorphs_globals.FREQUENCY_FILE_GENERATOR_DIALOG_NAME,
        )
    )
    return action


def create_readability_report_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Readability Report Generator", mw)
    action.setShortcut(am_config.shortcut_readability_report_generator)
    action.triggered.connect(
        partial(
            aqt.dialogs.open,
            name=ankimorphs_globals.READABILITY_REPORT_GENERATOR_DIALOG_NAME,
        )
    )
    return action


def create_test_action() -> QAction:
    keys = QKeySequence("Ctrl+T")
    action = QAction("&Test", mw)
    action.setShortcut(keys)
    action.triggered.connect(test_function)
    return action


def test_function() -> None:
    assert mw is not None
    assert mw.col.db is not None

    # am_db = AnkiMorphsDB()
    #
    # with am_db.con:
    #     result = am_db.con.execute(
    #         """
    #             SELECT morph_norm, morph_inflected, highest_learning_interval
    #             FROM Card_Morph_Map
    #             INNER JOIN Morphs ON
    #                     Card_Morph_Map.morph_norm = Morphs.norm AND Card_Morph_Map.morph_inflected = Morphs.inflected
    #             WHERE card_id = 1691325367067
    #             """
    #     ).fetchall()
    # print(f"result?: {result}")
    #
    # am_db.con.close()

    # print("Seen_Morphs:")
    # am_db = AnkiMorphsDB()
    # am_db.print_table("Seen_Morphs")
    # am_db.con.close()

    # card_id = 1691326508940
    # card: Card = mw.col.get_card(card_id)
    # card.queue = -1  # suspend
    # mw.col.update_card(card)

    # print(f"card: {Card}")
    # mid: NotetypeId = card.note().mid
    #
    # model_manager = mw.col.models
    # note_type_dict: Optional[NotetypeDict] = model_manager.get(mid)
    # assert note_type_dict is not None
    # new_field: FieldDict = model_manager.new_field("am-unknowns")
    #
    # model_manager.add_field(note_type_dict, new_field)
    # model_manager.update_dict(note_type_dict)

    # mw.col.update_note(note)


main()
