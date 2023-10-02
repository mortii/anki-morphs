import re


def non_span_sub(sub, repl, string):
    txt = ''
    for span in re.split('(<span.*?</span>)', string):
        if span.startswith('<span'):
            txt += span
        else:
            txt += ''.join(re.sub(sub, repl, span, flags=re.IGNORECASE))
    return txt
