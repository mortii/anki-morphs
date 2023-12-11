# Recalc

![recalc-tab.png](../../../img/recalc-tab.png)

* **Automatically Recalc before Anki sync**:  
  Recalc automatically runs before Anki syncs your card collection.
  > **Note**: If you use the [FSRS4Anki Helper add-on](https://ankiweb.net/shared/info/759844606) with an "Auto [...]
  after sync"-option enabled, then this can cause a bug where sync and recalc happen at the same time.
* **Suspend new cards with only known morphs**:  
  Cards that have either the ['All morphs known' tag](tags.md) or the ['Set known and skip' tag](tags.md) will be
  suspended on Recalc.
* **Minimum interval for known morphs**:  
  This is used when text is [highlighted](../../setup/settings/extra-fields.md#using-highlighted).