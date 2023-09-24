# Roadmap

MorphMan has significant technical-debt that needs to be paid off before adding any new functionality.

1. Expand automatic tests
    * Add a test collection and match it after recalc
    * Add tests for readability analyzer functions
2. Rebuild ui files
3. Add packages that increase code quality
   * Add mypy and gradually increase its strictness.
   * Add [vulture](https://github.com/jendrikseipp/vulture)
4. Remove intrinsic macab and jieba
5. Add advanced preferences tab
6. Fix recalc & databases
    * It is in desperate need of some deep cleaning to make it less obfuscated.
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
7. Fix undo-review
8. Improve file management
    * mm.py, cli.py, and glob.py
9. Make the focus morph field optional
    * Adding a focus morph field to cards is a significant pain point in the setup process and it's not _strictly_
      necessary for MorphMan to work