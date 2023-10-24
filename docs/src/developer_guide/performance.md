# Performance Profiling

[py-spy](https://pypi.org/project/py-spy/) is very nice because can run it without
changing any code in the project itself. You can
generate [flame graphs](https://www.brendangregg.com/FlameGraphs/cpuflamegraphs.html) using it which
you can then upload and view on [speedcode](https://www.speedscope.app/).

```bash
export PYTHONPATH=.
py-spy record -f speedscope -o profile.svg -- python3.9 tests/recalc_test.py
```
