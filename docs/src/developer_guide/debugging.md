# Debugging

Debugging tools for Anki add-ons are unfortunately fairly limited. The simplest approach is to use print statements
in the code which can then be seen in a terminal that spawned the Anki instance. Here is the guide for doing that:
[https://addon-docs.ankiweb.net/console-output.html#showing-the-console](https://addon-docs.ankiweb.net/console-output.html#showing-the-console)

Redirecting the terminal output to a file can be very useful. Here is a linux example:
```bash
anki > anki_output.txt
```

There is also a dedicated test function in the AnkiMorphs code that allows for faster/easier testing, you can
find it here: [\_\_init\_\_.py: test_function](https://github.com/mortii/anki-morphs/blob/aad52910c46c0abef84c58ac901efe470d9dcd48/ankimorphs/__init__.py#L537)
