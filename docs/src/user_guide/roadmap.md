# Roadmap

1. Fix undo-review
   1. Remove calls to mw.checkpoint() and mw.reset()
   2. migrate away from col.db.execute to col.update_notes / col.update_cards
   3. migrate from card.flush / note.flush to col.update_notes / col.update_cards
   4. display error if people are not using v3.
   5. on finish recalc function for query op (fsrs4sanki style)
   6. check if fsrs4anki concflicts with reviewing
   7. SearchNode brower utils
2. Try to made recalc undoable?
3. Remake highlighting feature
4. Implement spaCy
5. Remove old morphemizers
6. Remake readability analyzer
7. Allow for custom morph prioritization for specified languages (e.g. jp-morph-priority.txt)
8. Allow for a custom list of proper nouns that Anki-Morphs will automatically skip
9. Remake tests
10. Update guide
11. **Release AnkiMorphs stable version**
12. Implement optional "automatic recalc before sync"
13. Remake statistics page
14. Implement "cloze"-option [(#12)](https://github.com/mortii/anki-morphs/discussions/12)
