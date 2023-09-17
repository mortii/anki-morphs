# Tests

AnkiMorphs uses a combinations of unnittest and pytest.

## Guides

* [official pytest docs](https://docs.pytest.org/en/7.1.x/getting-started.html)
* [realpython pytest guide](https://realpython.com/pytest-python-testing/)
* [realpython Mocking External Libraries](https://realpython.com/testing-third-party-apis-with-mocks/)
* [realpython Python Mock Object Library](https://realpython.com/python-mock-library/)

## Pytest Add-ons

### pytest-randomly

* [pypi docs](https://pypi.org/project/pytest-randomly/)

Pytest plugin to randomly order tests to discover hidden flaws in the tests themselves, as well as giving a little more
coverage to your system.

### pytest-qt

* [official docs](https://pytest-qt.readthedocs.io/en/latest/intro.html)
* [Troubleshooting](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html)

pytest-qt is a pytest plugin that allows programmers to write tests for PyQt5, PyQt6, PySide2 and PySide6 applications.

### pytest-xvfb

* [pypi docs](https://pypi.org/project/pytest-xvfb/)

With Xvfb and the plugin installed, your testsuite automatically runs with Xvfb. This allows tests to be run without
windows popping up during GUI tests or on systems without a display (like a CI).

This is necessary for tests to work on github actions.


