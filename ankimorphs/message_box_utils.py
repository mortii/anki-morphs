from aqt.qt import QMessageBox, Qt, QWidget  # pylint:disable=no-name-in-module


def show_warning_box(
    title: str, body: str, parent: QWidget, use_markdown: bool = True
) -> bool:
    """
    Returns 'True' if user clicked 'Ok' button
    Returns 'False' otherwise.
    """
    warning_box = QMessageBox(parent)
    warning_box.setWindowTitle(title)
    warning_box.setIcon(QMessageBox.Icon.Warning)
    warning_box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    warning_box.setText(body)
    if use_markdown:
        warning_box.setTextFormat(Qt.TextFormat.MarkdownText)
    else:
        warning_box.setTextFormat(Qt.TextFormat.RichText)

    answer: int = warning_box.exec()
    if answer == QMessageBox.StandardButton.Yes:
        return True
    return False


def show_error_box(title: str, body: str, parent: QWidget) -> int:
    critical_box = QMessageBox(parent)
    critical_box.setWindowTitle(title)
    critical_box.setIcon(QMessageBox.Icon.Critical)
    critical_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    critical_box.setText(body)
    critical_box.setTextFormat(Qt.TextFormat.MarkdownText)
    answer: int = critical_box.exec()
    return answer


def confirm_new_extra_fields_selection(parent: QWidget) -> bool:
    title = "AnkiMorphs Confirmation"
    text = (
        'New "extra fields" have been selected in the settings, which will cause a full upload of your card'
        " collection the next time you synchronize.\n\nAny reviews or changes made on other devices that have"
        " yet to be synchronized will be lost when a full upload takes place.\n\nDo you still want to continue?"
    )
    answer = show_warning_box(title, text, parent=parent)
    return answer


# todo: rename
def warning_dialog(title: str, text: str, parent: QWidget) -> bool:
    answer = show_warning_box(title, text, parent=parent)
    if answer is True:
        return True
    return False
