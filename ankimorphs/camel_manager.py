from __future__ import annotations

import sys
from typing import Callable

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (  # pylint:disable=no-name-in-module
    QColor,
    QDialog,
    QIcon,
    QListWidgetItem,
    QPixmap,
    QSize,
    QStyle,
)
from aqt.utils import tooltip

from . import ankimorphs_globals as am_globals
from . import message_box_utils
from .extra_settings import extra_settings_keys
from .extra_settings.ankimorphs_extra_settings import AnkiMorphsExtraSettings
from .morphemizers import camel_wrapper
from .ui.camel_manager_dialog_ui import Ui_CamelManagerDialog


class CamelManagerDialog(QDialog):
    def __init__(
        self,
    ) -> None:
        assert mw is not None

        super().__init__(parent=None)  # no parent makes the dialog modeless
        self.ui = Ui_CamelManagerDialog()  # pylint:disable=invalid-name
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        camel_wrapper.load_camel_modules()

        self._setup_labels()
        self._setup_buttons()
        self._setup_icons()
        self._setup_list()

        self.am_extra_settings = AnkiMorphsExtraSettings()
        self.am_extra_settings.beginGroup(
            extra_settings_keys.Dialogs.CAMEL_MANAGER_WINDOW
        )
        self._setup_geometry()
        self.am_extra_settings.endGroup()

        self.show()

    def _setup_labels(self) -> None:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        status = "is" if camel_wrapper.successful_import else "is not"
        text = f"CAMeL Tools {status} installed for python {python_version}"
        self.ui.camelInstallationStatusLabel.setText(text)

    def _setup_icons(self) -> None:
        style: QStyle | None = self.style()
        assert style is not None

        transparent_pixmap = QPixmap(16, 16)
        transparent_pixmap.fill(QColor(0, 0, 0, 0))

        self.transparent_icon = QIcon(transparent_pixmap)
        self.apply_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)

    def _setup_buttons(self) -> None:
        self.ui.camelInstallPushButton.setAutoDefault(False)
        self.ui.purgeCamelPushButton.setAutoDefault(False)
        self.ui.installDatabasePushButton.setAutoDefault(False)
        self.ui.deleteDatabasePushButton.setAutoDefault(False)

        if camel_wrapper.successful_import:
            self.ui.purgeCamelPushButton.setEnabled(True)
            self.ui.camelInstallPushButton.setDisabled(True)
        else:
            self.ui.camelInstallPushButton.setEnabled(True)
            self.ui.purgeCamelPushButton.setDisabled(True)

        self.ui.installDatabasePushButton.setDisabled(True)
        self.ui.deleteDatabasePushButton.setDisabled(True)

        self.ui.camelInstallPushButton.clicked.connect(self._on_install_camel_clicked)
        self.ui.purgeCamelPushButton.clicked.connect(self._on_purge_camel_clicked)
        self.ui.installDatabasePushButton.clicked.connect(
            self._on_install_database_clicked
        )
        self.ui.deleteDatabasePushButton.clicked.connect(
            self._on_delete_database_clicked
        )

    def _on_install_camel_clicked(self) -> None:
        title = "Install CAMeL Tools"
        body = "Are you sure you want to download and install CAMeL Tools?"
        answer = message_box_utils.show_warning_box(title=title, body=body, parent=self)

        if not answer:
            return

        def _on_success() -> None:
            mw.progress.finish()
            message_box_utils.show_info_box(
                title="Success",
                body="Please restart Anki to load CAMeL Tools",
                parent=self,
            )

        self.ui.camelInstallPushButton.setDisabled(True)
        mw.progress.start(label="Downloading & Installing CAMeL Tools")

        operation = QueryOp(
            parent=self,
            op=lambda _: camel_wrapper.create_camel_venv(),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_purge_camel_clicked(self) -> None:
        title = "Purge CAMeL Tools"
        body = "Are you sure you want to uninstall CAMeL Tools and all databases?"
        answer = message_box_utils.show_warning_box(title=title, body=body, parent=self)

        if not answer:
            return

        def _on_success() -> None:
            mw.progress.finish()
            self.ui.purgeCamelPushButton.setDisabled(True)
            tooltip("Please restart Anki", period=5000, parent=self)

        operation = QueryOp(
            parent=self,
            op=lambda _: camel_wrapper.delete_camel_venv(),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_install_database_clicked(self) -> None:
        current_item: QListWidgetItem | None = self.ui.databasesListWidget.currentItem()
        assert current_item is not None

        db_name = current_item.data(DB_NAME_ROLE)
        display_name = current_item.text()

        _title = "Install database?"
        _body = f"Are you sure you want to download and install {display_name}?"
        if not message_box_utils.show_warning_box(
            title=_title, body=_body, parent=self
        ):
            return

        def _on_success() -> None:
            mw.progress.finish()
            message_box_utils.show_info_box(
                title="Success",
                body="Please restart Anki to reload databases",
                parent=self,
            )

        mw.progress.start(label=f"Downloading & Installing {display_name}")
        operation = QueryOp(
            parent=self,
            op=lambda _: camel_wrapper.install_database(db_name),
            success=lambda _: _on_success(),
        )
        operation.failure(self._on_failure)
        operation.with_progress().run_in_background()

    def _on_delete_database_clicked(self) -> None:
        message_box_utils.show_info_box(
            title="Not supported",
            body=(
                "Individual database deletion is not supported by CAMeL Tools.<br><br>"
                "Use <b>Purge CAMeL Tools</b> to remove everything, then reinstall "
                "only the databases you need."
            ),
            parent=self,
        )

    def _setup_list(self) -> None:
        self.ui.databasesListWidget.setIconSize(QSize(16, 16))
        self._populate_databases_list()

        self.ui.databasesListWidget.currentItemChanged.connect(
            self._toggle_database_action_buttons
        )

        if not camel_wrapper.successful_import:
            self.ui.databasesListWidget.setDisabled(True)

    def _populate_databases_list(self) -> None:
        installed_dbs = set(camel_wrapper.get_installed_databases())

        for db_name, display_name in camel_wrapper.available_databases.items():
            item = QListWidgetItem(display_name)
            item.setData(DB_NAME_ROLE, db_name)

            if db_name in installed_dbs:
                item.setIcon(self.apply_icon)
            else:
                item.setIcon(self.transparent_icon)

            self.ui.databasesListWidget.addItem(item)

    def _toggle_database_action_buttons(
        self,
        current_item: QListWidgetItem | None,
        _previous_item: QListWidgetItem | None,
    ) -> None:
        if current_item is not None:
            if current_item.icon().cacheKey() == self.apply_icon.cacheKey():
                self.ui.installDatabasePushButton.setDisabled(True)
                self.ui.deleteDatabasePushButton.setEnabled(True)
            else:
                self.ui.installDatabasePushButton.setEnabled(True)
                self.ui.deleteDatabasePushButton.setDisabled(True)
        else:
            self.ui.installDatabasePushButton.setDisabled(True)
            self.ui.deleteDatabasePushButton.setDisabled(True)

    def _setup_geometry(self) -> None:
        stored_geometry = self.am_extra_settings.value(
            extra_settings_keys.CamelManagerWindowKeys.WINDOW_GEOMETRY
        )
        if stored_geometry is not None:
            self.restoreGeometry(stored_geometry)

    def _on_failure(self, failure: Exception) -> None:
        mw.progress.finish()
        message_box_utils.show_error_box(
            title="Error",
            body=f"{failure}",
            parent=self,
        )

    def closeWithCallback(  # pylint:disable=invalid-name
        self, callback: Callable[[], None]
    ) -> None:
        self.am_extra_settings.camel_manager_window_settings(
            geometry=self.saveGeometry()
        )
        self.close()
        aqt.dialogs.markClosed(am_globals.CAMEL_MANAGER_DIALOG_NAME)
        callback()

    def reopen(self) -> None:
        self.show()


# Qt user data role for storing the db_name on list items
DB_NAME_ROLE = 256  # Qt.ItemDataRole.UserRole
