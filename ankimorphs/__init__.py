from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import (  # pylint:disable=no-name-in-module
    QAction,
    QDesktopServices,
    QMenu,
    QUrl,
)
from aqt.reviewer import Reviewer

from ankimorphs import (
    browser_utils,
    morph_stats,
    recalc,
    reviewing_utils,
    settings_dialog,
)
from ankimorphs.ankimorphs_db import AnkiMorphsDB
from ankimorphs.config import get_config
from ankimorphs.mecab_wrapper import get_morphemes_mecab

# A bug in the anki module leads to cyclic imports if these are placed higher
import anki.stats  # isort:skip pylint:disable=wrong-import-order
from anki import hooks  # isort:skip pylint:disable=wrong-import-order

mw.ANKIMORPHS_VERSION = "0.1-alpha"
TOOL_MENU = "am_tool_menu"
BROWSE_MENU = "am_browse_menu"
CONTEXT_MENU = "am_context_menu"


def main():
    # Support anki version 2.1.50 and above
    # Hooks should be placed in the order they are executed!

    # Adds the 'U: A:' to the toolbar  # TODO add recalc
    # gui_hooks.top_toolbar_did_init_links.append(add_morph_stats_to_toolbar)

    # Update the toolbar stats
    gui_hooks.profile_did_open.append(redraw_toolbar_wrapper)

    gui_hooks.profile_did_open.append(init_tool_menu_and_actions)
    gui_hooks.profile_did_open.append(replace_reviewer_functions)
    gui_hooks.profile_did_open.append(init_browser_menus_and_actions)

    # This stores the focus morphs seen today, necessary for the respective skipping option to work
    gui_hooks.reviewer_did_answer_card.append(mark_morph_seen_wrapper)


def redraw_toolbar_wrapper():
    # wrapping this makes testing easier because we don't have to mock mw
    mw.toolbar.draw()


def init_tool_menu_and_actions():
    for action in mw.form.menuTools.actions():
        if action.objectName() == TOOL_MENU:
            return  # prevents duplicate menus on profile-switch

    recalc_action = create_recalc_action()
    preferences_action = create_settings_action()
    guide_action = create_guide_action()
    changelog_action = create_changelog_action()

    am_tool_menu = create_am_tool_menu()
    am_tool_menu.addAction(recalc_action)
    am_tool_menu.addAction(preferences_action)
    am_tool_menu.addAction(guide_action)
    am_tool_menu.addAction(changelog_action)

    test_action = create_test_action()
    am_tool_menu.addAction(test_action)


def init_browser_menus_and_actions() -> None:
    view_action = create_view_morphs_action()
    learn_now_action = create_learn_now_action()
    browse_morph_action = create_browse_morph_action()
    already_known_tagger_action = create_already_known_tagger_action()

    def setup_browser_menu(_browser: Browser):
        browser_utils.browser = _browser

        for action in browser_utils.browser.form.menubar.actions():
            if action.objectName() == BROWSE_MENU:
                return  # prevents duplicate menus on profile-switch

        am_browse_menu = QMenu("AnkiMorphs", mw)
        am_browse_menu_creation_action = browser_utils.browser.form.menubar.addMenu(
            am_browse_menu
        )
        am_browse_menu_creation_action.setObjectName(BROWSE_MENU)

        am_browse_menu.addAction(view_action)
        am_browse_menu.addAction(learn_now_action)
        am_browse_menu.addAction(browse_morph_action)
        am_browse_menu.addAction(already_known_tagger_action)

    def setup_context_menu(_browser: Browser, context_menu: QMenu):
        for action in context_menu.actions():
            if action.objectName() == CONTEXT_MENU:
                return  # prevents duplicate menus on profile-switch

        context_menu_creation_action = context_menu.insertSeparator(view_action)
        context_menu.addAction(view_action)
        context_menu.addAction(learn_now_action)
        context_menu.addAction(browse_morph_action)
        context_menu.addAction(already_known_tagger_action)
        context_menu_creation_action.setObjectName(CONTEXT_MENU)

    gui_hooks.browser_menus_did_init.append(setup_browser_menu)

    gui_hooks.browser_will_show_context_menu.append(setup_context_menu)


def mark_morph_seen_wrapper(reviewer: Reviewer, card, ease):
    reviewing_utils.mark_morph_seen(card.note())


def replace_reviewer_functions() -> None:
    # This skips the cards the user specified in preferences GUI
    Reviewer.nextCard = hooks.wrap(
        Reviewer.nextCard, reviewing_utils.my_next_card, "around"
    )

    # Automatically highlights morphs on cards if the respective note stylings are present
    hooks.field_filter.append(reviewing_utils.highlight)

    Reviewer._shortcutKeys = hooks.wrap(
        Reviewer._shortcutKeys, reviewing_utils.my_reviewer_shortcut_keys, "around"
    )


def add_morph_stats_to_toolbar(links, toolbar) -> None:
    unique_name, unique_details = morph_stats.get_unique_morph_toolbar_stats()
    all_name, all_details = morph_stats.get_all_morph_toolbar_stats()
    links.append(
        toolbar.create_link(
            "morph",
            unique_name,
            morph_stats.on_morph_stats_clicked,
            tip=unique_details,
            id="morph",
        )
    )
    links.append(
        toolbar.create_link(
            "morph2",
            all_name,
            morph_stats.on_morph_stats_clicked,
            tip=all_details,
            id="morph2",
        )
    )


def create_am_tool_menu() -> QMenu:
    assert mw is not None
    am_tool_menu = QMenu("AnkiMorphs", mw)
    am_tool_menu_creation_action = mw.form.menuTools.addMenu(am_tool_menu)
    am_tool_menu_creation_action.setObjectName(TOOL_MENU)
    return am_tool_menu


def create_recalc_action() -> QAction:
    action = QAction("&Recalc", mw)
    action.setShortcut("Ctrl+M")
    action.triggered.connect(recalc.main)
    return action


def create_settings_action() -> QAction:
    action = QAction("&Settings", mw)
    action.setShortcut("Ctrl+O")
    action.triggered.connect(settings_dialog.main)
    return action


def create_guide_action() -> QAction:
    action = QAction("&Guide (web)", mw)
    action.triggered.connect(
        lambda: QDesktopServices.openUrl(
            QUrl("https://mortii.github.io/anki-morphs/user_guide/intro.html")
        )
    )
    return action


def create_changelog_action() -> QAction:
    action = QAction("&Changelog (web)", mw)
    action.triggered.connect(
        lambda: QDesktopServices.openUrl(
            QUrl("https://mortii.github.io/anki-morphs/user_guide/changelog.html")
        )
    )
    return action


def create_learn_now_action():
    action = QAction("&Learn Card Now", mw)
    action.setShortcut(get_config("shortcut_learn_now"))
    action.triggered.connect(browser_utils.run_learn_card_now)
    return action


def create_browse_morph_action():
    action = QAction("&Browse Same Morphs", mw)
    action.setShortcut(get_config("shortcut_browse_same_unknown_ripe"))
    action.triggered.connect(browser_utils.run_browse_morph)
    return action


def create_view_morphs_action() -> QAction:
    action = QAction("&View Morphemes", mw)
    action.setShortcut(get_config("shortcut_view_morphemes"))
    action.triggered.connect(browser_utils.run_view_morphs)
    return action


def create_already_known_tagger_action():
    action = QAction("&Tag As Known", mw)
    action.setShortcut(get_config("shortcut_set_known_and_skip"))
    action.triggered.connect(browser_utils.run_already_known_tagger)
    return action


def create_test_action() -> QAction:
    action = QAction("&Test", mw)
    action.setShortcut("Ctrl+T")
    action.triggered.connect(test_function)
    return action


def test_function() -> None:
    am_db = AnkiMorphsDB()
    with am_db.con:
        result = am_db.con.execute("SELECT count(*) FROM Card WHERE type=3")
        print(f"morphs: {result.fetchall()}")

    with am_db.con:
        result = am_db.con.execute(
            "SELECT * FROM Card_Morph_Map WHERE card_id=1691325537329"
        )
        print(f"Card_Morph_Map: {result.fetchall()}")

    am_db.con.close()


main()
