# Databases


### Anki dbs
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


