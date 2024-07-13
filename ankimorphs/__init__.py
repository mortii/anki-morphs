################################################################
#                          IMPORTS
################################################################
# We have to use implicit imports from the "ankimorphs" module
# because ankiweb changes the directory name to a number:
# "ankimorphs" -> "472573498"
#
# Correct:
# from . import browser_utils
#
# Incorrect (causes "not found" crashes):
# from ankimorphs import browser_utils
################################################################

import json
from functools import partial
from pathlib import Path
from typing import Literal

import aqt
from anki.cards import Card
from anki.collection import OpChangesAfterUndo
from aqt import gui_hooks, mw
from aqt.browser.browser import Browser
from aqt.overview import Overview
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
    ankimorphs_config,
    ankimorphs_globals,
    browser_utils,
    message_box_utils,
    name_file_utils,
    reviewing_utils,
    tags_and_queue_utils,
    toolbar_stats,
)
from .ankimorphs_config import AnkiMorphsConfig, AnkiMorphsConfigFilter
from .ankimorphs_db import AnkiMorphsDB
from .generators.generators_window import GeneratorWindow
from .progress.progress_window import ProgressWindow
from .known_morphs_exporter import KnownMorphsExporterDialog
from .recalc import recalc_main
from .settings import settings_dialog
from .settings.settings_dialog import SettingsDialog
from .tag_selection_dialog import TagSelectionDialog
from .toolbar_stats import MorphToolbarStats

_TOOL_MENU: str = "am_tool_menu"
_BROWSE_MENU: str = "am_browse_menu"
_CONTEXT_MENU: str = "am_context_menu"

_startup_sync: bool = True
_updated_seen_morphs_for_profile: bool = False


def main() -> None:
    # Support anki version 2.1.50 and above
    # Place hooks in the order they are executed

    gui_hooks.top_toolbar_did_init_links.append(init_toolbar_items)

    gui_hooks.profile_did_open.append(load_am_profile_configs)
    gui_hooks.profile_did_open.append(init_db)
    gui_hooks.profile_did_open.append(create_am_directories_and_files)
    gui_hooks.profile_did_open.append(register_addon_dialogs)
    gui_hooks.profile_did_open.append(redraw_toolbar)
    gui_hooks.profile_did_open.append(init_tool_menu_and_actions)
    gui_hooks.profile_did_open.append(init_browser_menus_and_actions)
    gui_hooks.profile_did_open.append(replace_reviewer_functions)

    gui_hooks.sync_will_start.append(recalc_on_sync)

    gui_hooks.webview_will_show_context_menu.append(add_text_as_name_action)
    gui_hooks.webview_will_show_context_menu.append(browse_study_morphs_for_text_action)

    gui_hooks.overview_did_refresh.append(update_seen_morphs)

    gui_hooks.reviewer_did_answer_card.append(insert_seen_morphs)

    gui_hooks.state_did_undo.append(rebuild_seen_morphs)

    gui_hooks.profile_will_close.append(clean_profile_session)


def init_toolbar_items(links: list[str], toolbar: Toolbar) -> None:
    # Adds the 'L: I:' and 'Recalc' to the toolbar

    morph_toolbar_stats = MorphToolbarStats()
    am_config = AnkiMorphsConfig()

    known_morphs_tooltip_message = (
        "L = Known Morph Lemmas<br>I = Known Morph Inflections"
    )

    if am_config.hide_recalc_toolbar is False:
        links.append(
            toolbar.create_link(
                cmd="recalc_toolbar",
                label="Recalc",
                func=recalc_main.recalc,
                tip="AnkiMorphs Recalc",
                id="recalc_toolbar",
            )
        )

    if am_config.hide_lemma_toolbar is False:
        links.append(
            toolbar.create_link(
                cmd="known_lemmas",
                label=morph_toolbar_stats.lemmas,
                func=lambda: tooltip(known_morphs_tooltip_message),
                tip="L = Known Morph Lemmas",
                id="known_lemmas",
            )
        )

    if am_config.hide_inflection_toolbar is False:
        links.append(
            toolbar.create_link(
                cmd="known_inflections",
                label=morph_toolbar_stats.inflections,
                func=lambda: tooltip(known_morphs_tooltip_message),
                tip="I = Known Morph Inflections",
                id="known_inflections",
            )
        )


def load_am_profile_configs() -> None:
    assert mw is not None

    profile_settings_path = Path(
        mw.pm.profileFolder(), ankimorphs_globals.PROFILE_SETTINGS_FILE_NAME
    )
    try:
        with open(profile_settings_path, encoding="utf-8") as file:
            profile_settings = json.load(file)
            ankimorphs_config.update_configs(profile_settings)
    except FileNotFoundError:
        # This is reached when we load a new anki profile that hasn't saved
        # any ankimorphs settings yet. It's important that we don't carry over
        # any settings from the previous profile because they can be somewhat
        # hidden (note filter tags), which could lead to completely unexpected
        # results for no apparent reason. We therefore reset meta.json to
        # config.json (default settings)
        ankimorphs_config.reset_all_configs()


def init_db() -> None:
    am_db = AnkiMorphsDB()
    am_db.create_all_tables()
    am_db.con.close()


def create_am_directories_and_files() -> None:
    assert mw is not None

    names_file_path: Path = Path(
        mw.pm.profileFolder(), ankimorphs_globals.NAMES_TXT_FILE_NAME
    )
    known_morphs_dir_path: Path = Path(
        mw.pm.profileFolder(), ankimorphs_globals.KNOWN_MORPHS_DIR_NAME
    )
    frequency_files_dir_path: Path = Path(
        mw.pm.profileFolder(), ankimorphs_globals.FREQUENCY_FILES_DIR_NAME
    )

    if not names_file_path.is_file():
        with open(names_file_path, mode="w", encoding="utf-8"):
            # just opening the file creates it
            pass

    if not known_morphs_dir_path.exists():
        Path(known_morphs_dir_path).mkdir()

    if not frequency_files_dir_path.exists():
        Path(frequency_files_dir_path).mkdir()


def register_addon_dialogs() -> None:
    # We use the Anki dialog manager to handle our dialogs

    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.SETTINGS_DIALOG_NAME, creator=SettingsDialog
    )
    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.GENERATOR_DIALOG_NAME,
        creator=GeneratorWindow,
    )
    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.PROGRESS_DIALOG_NAME,
        creator=ProgressWindow,
    )
    aqt.dialogs.register_dialog(
        name=ankimorphs_globals.KNOWN_MORPHS_EXPORTER_DIALOG_NAME,
        creator=KnownMorphsExporterDialog,
    )


def redraw_toolbar() -> None:
    # Updates the toolbar stats
    # Wrapping this makes testing easier because we don't have to mock mw
    assert mw is not None
    mw.toolbar.draw()


def init_tool_menu_and_actions() -> None:
    assert mw is not None

    for action in mw.form.menuTools.actions():
        if action.objectName() == _TOOL_MENU:
            return  # prevents duplicate menus on profile-switch

    am_config = AnkiMorphsConfig()

    settings_action = create_settings_action(am_config)
    recalc_action = create_recalc_action(am_config)
    generators_action = create_generators_dialog_action(am_config)
    progress_action = create_progress_dialog_action(am_config)
    known_morphs_exporter_action = create_known_morphs_exporter_action(am_config)
    reset_tags_action = create_tag_reset_action()
    guide_action = create_guide_action()
    changelog_action = create_changelog_action()

    am_tool_menu = create_am_tool_menu()
    am_tool_menu.addAction(settings_action)
    am_tool_menu.addAction(recalc_action)
    am_tool_menu.addAction(generators_action)
    am_tool_menu.addAction(progress_action)
    am_tool_menu.addAction(known_morphs_exporter_action)
    am_tool_menu.addAction(reset_tags_action)
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
    browse_morph_unknowns_lemma_action = create_browse_same_morph_unknowns_lemma_action(
        am_config
    )
    already_known_tagger_action = create_already_known_tagger_action(am_config)

    def setup_browser_menu(_browser: Browser) -> None:
        browser_utils.browser = _browser

        for action in browser_utils.browser.form.menubar.actions():
            if action.objectName() == _BROWSE_MENU:
                return  # prevents duplicate menus on profile-switch

        am_browse_menu = QMenu("AnkiMorphs", mw)
        am_browse_menu_creation_action = browser_utils.browser.form.menubar.addMenu(
            am_browse_menu
        )
        assert am_browse_menu_creation_action is not None
        am_browse_menu_creation_action.setObjectName(_BROWSE_MENU)
        am_browse_menu.addAction(view_action)
        am_browse_menu.addAction(learn_now_action)
        am_browse_menu.addAction(browse_morph_action)
        am_browse_menu.addAction(browse_morph_unknowns_action)
        am_browse_menu.addAction(browse_morph_unknowns_lemma_action)
        am_browse_menu.addAction(already_known_tagger_action)

    def setup_context_menu(_browser: Browser, context_menu: QMenu) -> None:
        for action in context_menu.actions():
            if action.objectName() == _CONTEXT_MENU:
                return  # prevents duplicate menus on profile-switch

        context_menu_creation_action = context_menu.insertSeparator(learn_now_action)
        assert context_menu_creation_action is not None
        context_menu.addAction(view_action)
        context_menu.addAction(learn_now_action)
        context_menu.addAction(browse_morph_action)
        context_menu.addAction(browse_morph_unknowns_action)
        context_menu.addAction(browse_morph_unknowns_lemma_action)
        context_menu.addAction(already_known_tagger_action)
        context_menu_creation_action.setObjectName(_CONTEXT_MENU)

    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
    gui_hooks.browser_will_show_context_menu.append(setup_context_menu)


def recalc_on_sync() -> None:
    # Anki automatically syncs on startup, but we want to avoid running
    # recalc at that time as it may be unnecessary.

    global _startup_sync

    if _startup_sync:
        _startup_sync = False
    else:
        am_config = AnkiMorphsConfig()
        if am_config.recalc_on_sync:
            recalc_main.recalc()


def replace_reviewer_functions() -> None:
    assert mw is not None

    mw.reviewer.nextCard = reviewing_utils.am_next_card

    mw.reviewer._shortcutKeys = partial(
        reviewing_utils.am_reviewer_shortcut_keys,
        self=mw.reviewer,
        _old=Reviewer._shortcutKeys,
    )


def insert_seen_morphs(
    _reviewer: Reviewer, card: Card, _ease: Literal[1, 2, 3, 4]
) -> None:
    """
    The '_reviewer' and '_ease' arguments are unused
    """
    am_db = AnkiMorphsDB()
    am_db.update_seen_morphs_today_single_card(card.id)
    am_db.con.close()


def update_seen_morphs(_overview: Overview) -> None:
    """
    The '_overview' argument is unused
    """
    # Overview is NOT the starting screen; it's the screen you see
    # when you click on a deck. This is a good time to run this function,
    # as 'seen morphs' only need to be known before starting a review.
    # Previously, this function was run on the profile_did_open hook,
    # but that sometimes caused interference with the add-on updater
    # since both occurred simultaneously.

    global _updated_seen_morphs_for_profile

    if _updated_seen_morphs_for_profile:
        return

    has_active_note_filter = False
    read_config_filters: list[AnkiMorphsConfigFilter] = (
        ankimorphs_config.get_read_enabled_filters()
    )

    for config_filter in read_config_filters:
        if config_filter.note_type != "":
            has_active_note_filter = True

    if has_active_note_filter:
        AnkiMorphsDB.rebuild_seen_morphs_today()

    _updated_seen_morphs_for_profile = True


def rebuild_seen_morphs(_changes: OpChangesAfterUndo) -> None:
    """
    The '_changes' argument is unused
    """

    ################################################################
    #                      TRACKING SEEN MORPHS
    ################################################################
    # We need to keep track of which morphs have been seen today,
    # which gets complicated when a user undos or redos cards.
    #
    # When a card is answered/set known, we insert all the card's
    # morphs into the 'Seen_Morphs'-table. If a morph is already
    # in the table, we just ignore the insert error. This makes
    # it tricky to remove morphs from the table when undo is used
    # because we don't track if the morphs were already in the table
    # or not. To not deal with this removal problem, we just drop
    # the entire table and rebuild it with the morphs of all the
    # studied cards. This is costly, but it only happens on 'undo',
    # which should be a rare occurrence.
    #
    # REDO:
    # Redoing, i.e., undoing an undo (Ctrl+Shift+Z), is almost
    # impossible to distinguish from a regular forward operation.
    # Since this is such a nightmare to deal with (and is hopefully
    # a rare occurrence), this will just be left as unexpected behavior.
    ################################################################
    AnkiMorphsDB.rebuild_seen_morphs_today()

    if ankimorphs_globals.DEV_MODE:
        print("Seen_Morphs:")
        am_db = AnkiMorphsDB()
        am_db.print_table("Seen_Morphs")
        am_db.con.close()


def clean_profile_session() -> None:
    global _updated_seen_morphs_for_profile
    _updated_seen_morphs_for_profile = False
    AnkiMorphsDB.drop_seen_morphs_table()


def reset_am_tags() -> None:
    assert mw is not None

    am_config = AnkiMorphsConfig()

    title = "Reset Tags?"
    body = (
        'Clicking "Yes" will remove the following tags from all cards:\n\n'
        f"- {am_config.tag_known_automatically}\n\n"
        f"- {am_config.tag_ready}\n\n"
        f"- {am_config.tag_not_ready}\n\n"
        f"- {am_config.tag_fresh}\n\n"
    )
    want_reset = message_box_utils.show_warning_box(title, body, parent=mw)
    if want_reset:
        tags_and_queue_utils.reset_am_tags(parent=mw)


def create_am_tool_menu() -> QMenu:
    assert mw is not None
    am_tool_menu = QMenu("AnkiMorphs", mw)
    am_tool_menu_creation_action = mw.form.menuTools.addMenu(am_tool_menu)
    assert am_tool_menu_creation_action is not None
    am_tool_menu_creation_action.setObjectName(_TOOL_MENU)
    return am_tool_menu


def create_recalc_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Recalc", mw)
    action.setShortcut(am_config.shortcut_recalc)
    action.triggered.connect(recalc_main.recalc)
    return action


def create_settings_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Settings", mw)
    action.setShortcut(am_config.shortcut_settings)
    action.triggered.connect(
        partial(aqt.dialogs.open, name=ankimorphs_globals.SETTINGS_DIALOG_NAME)
    )
    return action


def create_tag_reset_action() -> QAction:
    action = QAction("&Reset Tags", mw)
    action.triggered.connect(reset_am_tags)
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


def create_browse_same_morph_unknowns_lemma_action(
    am_config: AnkiMorphsConfig,
) -> QAction:
    action = QAction("&Browse Same Unknown Morphs (Lemma)", mw)
    action.setShortcut(am_config.shortcut_browse_ready_same_unknown_lemma)
    action.triggered.connect(
        partial(
            browser_utils.run_browse_morph, search_unknowns=True, search_lemma_only=True
        )
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


def add_text_as_name_action(web_view: AnkiWebView, menu: QMenu) -> None:
    assert mw is not None
    selected_text = web_view.selectedText()
    if selected_text == "":
        return
    action = QAction("Mark as name", menu)
    action.triggered.connect(lambda: name_file_utils.add_name_to_file(selected_text))
    action.triggered.connect(AnkiMorphsDB.insert_names_to_seen_morphs)
    action.triggered.connect(mw.reviewer.bury_current_card)
    menu.addAction(action)


def browse_study_morphs_for_text_action(web_view: AnkiWebView, menu: QMenu) -> None:
    selected_text = web_view.selectedText()
    if selected_text == "":
        return
    action = QAction(f"Browse in {ankimorphs_globals.EXTRA_FIELD_STUDY_MORPHS}", menu)
    action.triggered.connect(
        lambda: browser_utils.browse_study_morphs_for_highlighted_morph(selected_text)
    )
    menu.addAction(action)


def create_generators_dialog_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Generators", mw)
    action.setShortcut(am_config.shortcut_generators)
    action.triggered.connect(
        partial(
            aqt.dialogs.open,
            name=ankimorphs_globals.GENERATOR_DIALOG_NAME,
        )
    )
    return action

def create_progress_dialog_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Progress", mw)
    action.setShortcut(am_config.shortcut_progress)
    action.triggered.connect(
        partial(
            aqt.dialogs.open,
            name=ankimorphs_globals.PROGRESS_DIALOG_NAME,
        )
    )
    return action


def create_known_morphs_exporter_action(am_config: AnkiMorphsConfig) -> QAction:
    action = QAction("&Known Morphs Exporter", mw)
    action.setShortcut(am_config.shortcut_known_morphs_exporter)
    action.triggered.connect(
        partial(
            aqt.dialogs.open,
            name=ankimorphs_globals.KNOWN_MORPHS_EXPORTER_DIALOG_NAME,
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
    # To activate this dev function in Anki:
    # 1. In ankimorphs_globals.py set 'DEV_MODE = True'
    # 2. Use Ctrl+T, or go to: Tools -> Ankimorphs -> Test

    assert mw is not None
    assert mw.col.db is not None

    am_db = AnkiMorphsDB()

    # print("Morphs:")
    # am_db.print_table("Morphs")

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

    # card_id = 1720345836169
    # card = mw.col.get_card(card_id)
    # card.ivl += 30
    # mw.col.update_card(card)

    am_db.con.close()


main()
