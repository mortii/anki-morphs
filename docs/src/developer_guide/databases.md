# Databases

## ankimorphs.db

This is an sqlite database with 3 tables:

```
'Card'
'Card_Morph_Map'
'Morph'
```

A card can have many morphs,
morphs can be on many cards,
so we need a many-to-many db structure:

```
Card -> Card_Morph_Map <- Morph
```

### Card table

```roomsql
id INTEGER PRIMARY KEY ASC,  
type INTEGER,
interval INTEGER
```

### Card_Morph_Map table

```roomsql
card_id INTEGER,
morph_norm TEXT,
morph_inflected TEXT,
FOREIGN KEY(card_id) REFERENCES card(id),
FOREIGN KEY(morph_norm, morph_inflected) REFERENCES morph(norm, inflected)
```

### Morph table

```roomsql
norm TEXT,
base TEXT,
inflected TEXT,
read TEXT,
pos TEXT,
sub_pos TEXT,
is_base INTEGER,
PRIMARY KEY (norm, inflected)
```

To make sure the morphs are unique we make the primary key norm (base) AND inflection (derivative), since inflections
can be identical even if they are derived from two different base, eg:

```
Inflection : Base
ある : 有る
ある : 或る
```

Using an int as a primary key is preferable over text objects, but hashing the norm and base would lead to a high
likelihood of collisions because of the following:

    # sqllite integers are max 2^(63)-1 = 9,223,372,036,854,775,807
    # The chance of hash collision is 50% when sqrt(2^(n/2)) where n is bits of the hash
    # With 64 bits the prob of collision becomes sqrt(2^(64/2)) = 65,536

So if we have over 65,536 morphs we will probably experience bugs that basically impossible to trace. 

## Anki dbs

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
[[0, 'id', 'INTEGER', 0, None, 1],
[1, 'nid', 'INTEGER', 1, None, 0],
[2, 'did', 'INTEGER', 1, None, 0],
[3, 'ord', 'INTEGER', 1, None, 0],
[4, 'mod', 'INTEGER', 1, None, 0],
[5, 'usn', 'INTEGER', 1, None, 0],
[6, 'type', 'INTEGER', 1, None, 0],
[7, 'queue', 'INTEGER', 1, None, 0],
[8, 'due', 'INTEGER', 1, None, 0],
[9, 'ivl', 'INTEGER', 1, None, 0],
[10, 'factor', 'INTEGER', 1, None, 0],
[11, 'reps', 'INTEGER', 1, None, 0],
[12, 'lapses', 'INTEGER', 1, None, 0],
[13, 'left', 'INTEGER', 1, None, 0],
[14, 'odue', 'INTEGER', 1, None, 0],
[15, 'odid', 'INTEGER', 1, None, 0],
[16, 'flags', 'INTEGER', 1, None, 0],
[17, 'data', 'TEXT', 1, None, 0]]
```


