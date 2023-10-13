# Roadmap

1. Make the am_next_card function a background op and display number of skipped card in a pop-up dialog
2. Fix set_known_and_skip to show tooltip "skipped x cards"
3. Add option to suspend stale cards... without this feature thousands of cards might be buried at the start of
   every review. Probably make suspending the default behaviour.
4. Implement option to move all suspended cards to the end of the queue?
5. Implement optional automatic recalc before sync
6. Try to improve caching by using inner join on notes and cards query
7. Improve card difficulty algorithm (it is no longer constrained by card.due backend)
    1. Sum the difficulty of the individual morphs in the field
8. Rename default ankimorphs tags?
9. Add conflicting add-ons to config
10. Release AnkiMorphs alpha-test version?
11. Remake highlighting feature
12. Fix undo-review
13. Implement spaCy
14. Remove intrinsic morphemizers (takes up unnecessary space)
15. Allow for custom morph prioritization for specified lagnuages (e.g. jp-morph-priority.txt)
16. Remake tests
17. Add [vulture](https://github.com/jendrikseipp/vulture) to pre-commit
18. Update guide
19. Release AnkiMorphs stable version?
20. Remake statistics page
21. Remake readability analyzer



