# Roadmap

1. Fix undo-review
   2. migrate away from col.db.execute to col.update_notes / col.update_cards
   4. on finish recalc function for query op (fsrs4sanki style)
   5. check if fsrs4anki concflicts with reviewing
   6. SearchNode brower utils
2. check thread on_failure
3. escape tags in browser utils
3. use re.sub for quotation marks
4. Try to made recalc undoable?
5. Remake highlighting feature
6. Implement spaCy
7. Remove old morphemizers
8. Remake readability analyzer
9. Allow for custom morph prioritization for specified languages (e.g. jp-morph-priority.txt)
10. Allow for a custom list of proper nouns that Anki-Morphs will automatically skip
11. Remake tests
12. Update guide
13. **Release AnkiMorphs stable version**
14. Implement optional "automatic recalc before sync"
15. Remake statistics page
16. Implement "cloze"-option [(#12)](https://github.com/mortii/anki-morphs/discussions/12)
