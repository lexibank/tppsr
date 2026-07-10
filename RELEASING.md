# Releasing TPPSR

```shell
pip install -e .[test]
```


```shell
cldfbench lexibank.makecldf lexibank_tppsr.py --glottolog-version v5.3 --clts-version v2.3.0 --concepticon-version v3.4.0
```

```shell
pytest
```

```shell
cldfbench cldfreadme lexibank_tppsr.py
cldfbench cldfviz.map cldf/ --language-properties Canton --out map.svg --format svg
```
