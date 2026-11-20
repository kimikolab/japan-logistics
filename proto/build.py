"""core.js とデータを template.html に埋め込み、単体の index.html を作る。"""
import pathlib
here = pathlib.Path(__file__).parent; data = here.parent / "data"
t = (here / "template.html").read_text(encoding="utf-8")
core = (here / "core.js").read_text(encoding="utf-8").split("if (typeof module")[0]
t = t.replace("/*CORE*/", core).replace("/*CITIES*/", (data / "cities.json").read_text(encoding="utf-8")).replace("/*GEO*/", (data / "geo.json").read_text(encoding="utf-8"))
(here / "index.html").write_text(t, encoding="utf-8"); print("index.html", len(t))
