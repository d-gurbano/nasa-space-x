"""CLI:  python -m rewind_engine <command> --objects <first|csv|slug,slug> [--out SITE]

commands:
  prepare    MOST + Horizons frame tables
  fetch      download stamps + static-sky references (run detached with nohup; resumable)
  measure    photometry, controls, injection, clone search, orbit check, verdict
  site       write the website files
  run        prepare + fetch (inline) + measure + site
  benchmark  "pretend it is new" test on known asteroids
"""
import argparse
import sys

from . import config as C


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rewind_engine")
    ap.add_argument("command", choices=["prepare", "fetch", "measure", "site", "run", "benchmark", "train", "autosite"])
    ap.add_argument("--objects", default="first")
    ap.add_argument("--out", default=C.SITE)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-refs", action="store_true")
    ap.add_argument("--stage", default="all", choices=["all", "fetch", "measure"], help="benchmark stage")
    a = ap.parse_args(argv)
    C.SITE = a.out
    C.ensure_dirs()
    from . import objects as O
    objs = O.load_objects(a.objects) if a.command not in ("benchmark", "train") else None
    if a.command == "prepare":
        from . import frames as F
        for o in objs.itertuples():
            fr = F.prepare(o)
            print(o.slug, len(fr), flush=True)
    elif a.command == "fetch":
        from . import fetch
        fetch.run(objs, workers=a.workers, refs=not a.no_refs)
    elif a.command == "measure":
        from . import pipeline
        pipeline.measure_all(objs)
    elif a.command == "site":
        from . import site
        site.write_all(objs)
    elif a.command == "run":
        from . import fetch, pipeline, site
        fetch.run(objs, workers=a.workers, refs=not a.no_refs)
        pipeline.measure_all(objs)
        site.write_all(objs)
    elif a.command == "benchmark":
        from . import benchmark
        if a.stage in ("all", "fetch"):
            benchmark.fetch_cases()
        if a.stage in ("all", "measure"):
            benchmark.run()
    elif a.command == "autosite":
        from . import autosite
        autosite.run(objs)
    elif a.command == "train":
        from . import realfake
        realfake.train()


if __name__ == "__main__":
    sys.exit(main())
