from aqt.qt import QMessageBox, Qt, QWidget  # pylint:disable=no-name-in-module


def show_warning_box(title: str, body: str, parent: QWidget) -> bool:
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
    warning_box.setTextFormat(Qt.TextFormat.MarkdownText)
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
