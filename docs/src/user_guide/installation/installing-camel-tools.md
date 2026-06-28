# Installing CAMeL Tools

CAMeL Tools is an Arabic NLP library developed by the CAMeL Lab at NYU Abu Dhabi. It provides proper
morphological analysis for Arabic, recognizing that `الكتاب` and `كتاب` share the same lemma — something
the Simple Space Splitter cannot do.

From the Anki `Tools` menu, navigate to `AnkiMorphs` → `CAMeL Tools Manager`.

## Step 1: Install CAMeL Tools

Click **Install CAMeL Tools**. This downloads and installs CAMeL Tools into a dedicated virtual environment
inside your Anki add-ons folder. After installation completes, **restart Anki**.

> **System requirements** (per the [CAMeL Tools installation docs](https://github.com/CAMeL-Lab/camel_tools#installation)):
> - Python 3.11–3.14, 64-bit (Anki's bundled Python must meet this requirement)
> - The [Rust compiler](https://rustup.rs) must be installed
> - macOS/Linux: `cmake` and `boost` must be installed before clicking Install
>   - macOS: `brew install cmake boost`
>   - Ubuntu/Debian: `sudo apt-get install cmake libboost-all-dev`
> - Windows: no extra system dependencies beyond Python and Rust are required

> **Apple Silicon (M1/M2/M3):** No extra steps are required — the installer detects Apple Silicon and sets
> the correct build architecture flag automatically. This note is just reassurance; there is nothing for you
> to configure.

## Step 2: Install a Database

After restarting Anki, open the CAMeL Tools Manager again. The databases list shows the available Arabic
morphology databases:

| Database | Dialect | License | Download size |
|---|---|---|---|
| Modern Standard Arabic (`calima-msa-r13`) | MSA | GPL v2 | 40.5 MB |
| Egyptian Arabic (`calima-egy-r13`) | Egyptian | GPL v2 | 67.3 MB |
| Gulf Arabic (`calima-glf-01`) | Gulf | CC BY 4.0 | 8.0 MB |

> **Note:** You only need the database(s) for the dialect(s) you study — you do **not** have to install all
> three (≈ 116 MB if you install every one). Each database is downloaded once and reused. The numbers above
> are the only data AnkiMorphs downloads; CAMeL Tools also ships much larger optional models (its full `all`
> bundle is several GB), but AnkiMorphs never downloads those.
>
> Sizes are from the [CAMeL Tools data packages reference](https://camel-tools.readthedocs.io/en/latest/reference/packages.html).

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
