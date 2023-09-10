# Databases

_These notes are from 2020 and may be outdated!_

## Sqlite support

A new option called saveSQLite has been added. If True, a sqlite database called morphman.sqlite is created.  The
default of this option is True

The schema of this database is straighforward:

### morphs

this is the table that contains the morphs. The "inflected" field is the actual word.

``` sql
CREATE TABLE morphs (
morphid, norm, base, inflected, read, pos, subpos,
primary key (morphid));
```

### location

This are the notes where a given morph is located, and some information about it (some is redundant, such as the actual value of the field, which can be extracted from
anki's database, but morphan saves it, so it is saved).

Most fields are self-explanatory. maturity is days to next review (0 for non-reviewed)... mmm, maybe i am missing some words if the review is in less than 1 day... then... what if it is the first day or reviews...
guid (I don't know), and weight ... mmmm, it is 1 in all cases. I guess it is not used


``` sql
CREATE TABLE locations (
morphid, noteid, field, fieldvalue, maturity, guid, weight,
primary key (morphid, noteid, field),
foreign key (morphid) references morphs
);
``` 

## dump_db.py

the script scripts/dump_db.py can be used to dump the pickled databases (.db)
from the command line. Simply run

``` bash
python3 scripts/dump_db.py <picked-database-file> locations
```

The output is straighforward:

For every moprh, it prints its information and the noteid, fieldname, fieldvalue, maturity (in days), guid and the weight.
See the documentation of Location (under sqlite3) above.

Output is sorted by morph, the locations. If the locations parameter is not specified, only output morphs

```
norm	base	inflected	reading	pos	subpos
が	が	が	ガ	助詞	格助詞
1487630686818	Expression	138	q^h7dzq%1n	1
1487630686856	Expression	168	mX1IuArU9S	1
1487630686913	Expression	277	v-,8t@ro!L	1
1487630686948	Expression	193	kux^L#r]R4	1
1487630687083	Expression	288	nD){h(39!I	1
1487630687241	Expression	320	gTy?mxI5y]	1
1489462758327	Expression	198	lQ@.k1)U[8	1
1489462758391	Expression	103	fd[asSdN3~	1
1489462776809	Expression	114	g@A7}LZ#;&	1
1489462791313	Expression	54	IR)(c(9dd6	1
1536650897908	sentenceJp	147	i[{pI;:U>|	1
1536650897940	sentenceJp	259	d>&JX6S_Bd	1
1536650898064	sentenceJPnuke	45	DJgfwS>YL^	1
1536650898337	sentenceJp	23	ez^L$2ON)M	1
1536651281457	sentenceJp	22	o!aP/}@6+5	1
1536651299859	sentenceJp	200	CcH+l<Y_td	1
1536651300085	sentenceJp	22	C.!^yST7m8	1
1536651300164	sentenceJp	22	fnM.#k3}En	1
```