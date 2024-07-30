# Databases

## ankimorphs.db

This is an sqlite database with three tables:

```
'Cards'
'Card_Morph_Map'
'Morphs'
```

A card can have many morphs,
morphs can be on many cards,
so we need a many-to-many db structure:

```
Cards -> Card_Morph_Map <- Morphs
```

### Card table

```roomsql
card_id INTEGER PRIMARY KEY ASC,
note_id INTEGER,
note_type_id INTEGER,
card_type INTEGER,
tags TEXT
```

### Card_Morph_Map table

```roomsql 
card_id INTEGER,
morph_lemma TEXT,
morph_inflection TEXT,
FOREIGN KEY(card_id) REFERENCES card(id),
FOREIGN KEY(morph_lemma, morph_inflection) REFERENCES morph(lemma, inflection)
```

### Morph table

```roomsql
lemma TEXT,
inflection TEXT,
highest_learning_interval INTEGER,
PRIMARY KEY (lemma, inflection)
```

To make sure the morphs are unique, we make the primary key the lemma AND inflection, since inflections
can be identical even if they are derived from two different bases, eg:

```
Inflection : Lemma
ある : 有る
ある : 或る
```

Using an int as a primary key is preferable over text objects, but hashing the lemma and inflection would lead to a high
likelihood of collisions because of the following:

    # sqlite integers are max 2^(63)-1 = 9,223,372,036,854,775,807
    # The chance of hash collision is 50% when sqrt(2^(n/2)) where n is bits of the hash
    # With 64 bits the prob of collision becomes sqrt(2^(64/2)) = 65,536

So if we have over 65,536 morphs we would likely experience bugs that are basically impossible to trace. 

## Anki dbs

        table_info = mw.col.db.execute("PRAGMA table_info('decks');")
        print(f"table_info: {result}")

Anki collection db tables:

```
[['col'],
['notes'],
['cards'],
['revlog'],
['deck_config'],
['config'],
['fields'],
['templates'],
['notetypes'],
['decks'],
['sqlite_stat1'],
['sqlite_stat4'],
['tags'],
['graves']]
```

notes table:

```
[[0, 'id', 'INTEGER', 0, None, 1],
[1, 'guid', 'TEXT', 1, None, 0],
[2, 'mid', 'INTEGER', 1, None, 0],
[3, 'mod', 'INTEGER', 1, None, 0],
[4, 'usn', 'INTEGER', 1, None, 0],
[5, 'tags', 'TEXT', 1, None, 0],
[6, 'flds', 'TEXT', 1, None, 0],
[7, 'sfld', 'INTEGER', 1, None, 0],
[8, 'csum', 'INTEGER', 1, None, 0],
[9, 'flags', 'INTEGER', 1, None, 0],
[10, 'data', 'TEXT', 1, None, 0]]
```

notetypes table:

```
[[0, 'id', 'INTEGER', 1, None, 1],
[1, 'name', 'TEXT', 1, None, 0],
[2, 'mtime_secs', 'INTEGER', 1, None, 0],
[3, 'usn', 'INTEGER', 1, None, 0],
[4, 'config', 'BLOB', 1, None, 0]]
```

cards table:

```
'id'     ID_FIELD_NUMBER: builtins.int
'nid'    NOTE_ID_FIELD_NUMBER: builtins.int
'did'    DECK_ID_FIELD_NUMBER: builtins.int
'ord'    TEMPLATE_IDX_FIELD_NUMBER: builtins.int
'mod'    MTIME_SECS_FIELD_NUMBER: builtins.int  # when card was modified
'usn'    USN_FIELD_NUMBER: builtins.int
'type'   CTYPE_FIELD_NUMBER: builtins.int
'queue'  QUEUE_FIELD_NUMBER: builtins.int
'due'    DUE_FIELD_NUMBER: builtins.int
'ivl'    INTERVAL_FIELD_NUMBER: builtins.int
'factor' EASE_FACTOR_FIELD_NUMBER: builtins.int
'reps'   REPS_FIELD_NUMBER: builtins.int
'lapses' LAPSES_FIELD_NUMBER: builtins.int
'left'   REMAINING_STEPS_FIELD_NUMBER: builtins.int
'odue'   ORIGINAL_DUE_FIELD_NUMBER: builtins.int
'odid'   ORIGINAL_DECK_ID_FIELD_NUMBER: builtins.int
'flags'  FLAGS_FIELD_NUMBER: builtins.int
'data'   custum_data builtins.str
```

'type' is the learning stage type:
```
CardType = NewType("CardType", int)
CARD_TYPE_NEW = CardType(0)
CARD_TYPE_LRN = CardType(1)
CARD_TYPE_REV = CardType(2)
CARD_TYPE_RELEARNING = CardType(3)
```


'queue' types:
```
CardQueue = NewType("CardQueue", int)
QUEUE_TYPE_MANUALLY_BURIED = CardQueue(-3)
QUEUE_TYPE_SIBLING_BURIED = CardQueue(-2)
QUEUE_TYPE_SUSPENDED = CardQueue(-1)
QUEUE_TYPE_NEW = CardQueue(0)
QUEUE_TYPE_LRN = CardQueue(1)
QUEUE_TYPE_REV = CardQueue(2)
QUEUE_TYPE_DAY_LEARN_RELEARN = CardQueue(3)
QUEUE_TYPE_PREVIEW = CardQueue(4)
```

