# Installing CAMeL Tools

CAMeL Tools is an Arabic NLP library developed by the CAMeL Lab at NYU Abu Dhabi. It provides proper
morphological analysis for Arabic, recognizing that `الكتاب` and `كتاب` share the same lemma — something
the Simple Space Splitter cannot do.

From the Anki `Tools` menu, navigate to `AnkiMorphs` → `CAMeL Tools Manager`.

## Step 1: Install CAMeL Tools

Click **Install CAMeL Tools**. This downloads and installs CAMeL Tools into a dedicated virtual environment
inside your Anki add-ons folder. After installation completes, **restart Anki**.

> **System requirements:**
> - Python 3.11 or newer (Anki's bundled Python must meet this requirement)
> - macOS/Linux: `cmake` and `boost` must be installed before clicking Install
>   - macOS: `brew install cmake boost`
>   - Ubuntu/Debian: `sudo apt-get install cmake libboost-all-dev`
> - The Rust compiler must be installed: [rustup.rs](https://rustup.rs)

> **Apple Silicon (M1/M2/M3):** The installer sets the correct build flag automatically.

## Step 2: Install a Database

After restarting Anki, open the CAMeL Tools Manager again. The databases list shows the available Arabic
morphology databases:

| Database | Dialect | License |
|---|---|---|
| Modern Standard Arabic (`calima-msa-r13`) | MSA | GPL v2 |
| Egyptian Arabic (`calima-egy-r13`) | Egyptian | GPL v2 |
| Gulf Arabic (`calima-glf-01`) | Gulf | CC BY 4.0 |

Select the database you want, then click **Install Database**. The data files are downloaded to
`~/.camel_tools/` on macOS/Linux or `%APPDATA%\camel_tools\` on Windows.

After installation completes, **restart Anki** again. The morphemizer will now appear in the
Settings → Note Filter dropdown as e.g. `CAMeL Tools: Egyptian Arabic`.

## Purging CAMeL Tools

Click **Purge CAMeL Tools** to remove the entire CAMeL Tools virtual environment. This does not remove
the downloaded database files in `~/.camel_tools/` — those can be deleted manually if needed.

## License Note

The MSA and Egyptian Arabic databases (`calima-msa-r13`, `calima-egy-r13`) are derived from the ALMOR
database distributed with MADAMIRA (Columbia University) and are licensed under **GPL v2**. The Gulf Arabic
database (`calima-glf-01`) is licensed under **CC BY 4.0**. The CAMeL Tools Python library itself is MIT
licensed. Users download the databases directly from the CAMeL Tools data repository.
