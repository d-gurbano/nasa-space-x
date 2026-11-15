"""One final, clean pass: re-measure every object under the final rules, rebuild every site file, write the
verdict table (docs/RESULTS.md), then mark index.json final."""
from __future__ import annotations

import time

from . import objects as O
from . import report, results_table, site


def run(extra_md=""):
    objs = O.load_objects("first")
    t0 = time.time()
    for o in objs.itertuples():
        try:
            report.run_object(o)
        except Exception as e:  # noqa
            print(f"{o.slug}: measure failed: {e}", flush=True)
    site.write_all(objs)                      # pages already written; static files, detectives, index
    md = results_table.write(extra_md)
    site.rebuild_index(final=True)
    print(md)
    print(f"final pass done in {time.time() - t0:.0f} s", flush=True)
