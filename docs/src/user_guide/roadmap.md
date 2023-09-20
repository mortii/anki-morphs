# Roadmap

MorphMan has significant technical-debt that needs to be paid off before adding any new functionality.

1. Expand automatic tests before refactoring the code
    * Add a test collection and match it after recalc
    * Add tests for readability analyzer functions
    * https://pypa-build.readthedocs.io/en/stable/test_suite.html
    * https://pypa-build.readthedocs.io/en/stable/index.html
2. suuper clean!! https://github.com/sourcery-ai/python-best-practices-cookiecutter
   * others: https://github.com/topics/cookiecutter-template
   * https://stackoverflow.com/questions/46330327/how-are-pipfile-and-pipfile-lock-used
   * https://packaging.python.org/en/latest/tutorials/packaging-projects/
3. Add packages that incraese code quality
   * Add mypy and gradually increase its strictness.
   * Add flake8 alongside pylint for better coverage
   * Add [black](https://github.com/psf/black)
   * Add [isort](https://pypi.org/project/isort/8)
   * Add [vulture](https://github.com/jendrikseipp/vulture)
4. add isort to pre-commit: https://pycqa.github.io/isort/docs/configuration/pre-commit.html
5. travis cli: https://docs.travis-ci.com/user/customizing-the-build/
6. remove intrinsic macab 
7. Rename to ankimorphs, figure out how to version the addon...
8. Fix configs
    * Migrate from config.py to [config.json and user_files](https://addon-docs.ankiweb.net/addon-config.html)
    * Refactor preferences.py and make configs more robust
9. Fix recalc & databases
    * main.py needs a more fitting name, recalc.py would make more sense. It is also in desperate need of some deep
      cleaning to make it less obfuscated.
    * Improve MMI
        * Separate the priorities and make them explicit and exclusive (collection frequency and frequency.txt)
        * The usefulness variable is not great and the rounding is lossy. Ideally no cards should get the same MMI.
        * Add a user adjustable bias to sentence length on top of the 'ideal sentence length' variable. Shorter sentences
          are usually better for learning.
    * Improve databases
        * Migrate from pickle to sqlite or some other database system
        * The databases have unnecessarily overlapping data which make them less useful...
        * known.db is a misleading name, it contains all morphs ever seen.
        * Refactor morphemes.py and move the different classes into separate files instead.
10. Improve file management
     * mm.py, cli.py, and glob.py
11. Make the focus morph field optional
     * Adding a focus morph field to cards is a significant pain point in the setup process and it's not _strictly_
       necessary for MorphMan to work
12. Add support for Korean?