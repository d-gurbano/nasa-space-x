"""Kaggle kernel rewind-c2-pack: tar the outputs of the kernels attached as kernel_sources, one tar per kernel,
so the Mac downloads a few files instead of ~20,000 small PNGs (the CLI fetches output files one by one)."""
import os
import tarfile

OUT = "/kaggle/working"
for d, dirs, files in os.walk("/kaggle/input", followlinks=True):
    if "run_log.txt" in files and "work" in dirs:  # a K1 output folder
        name = os.path.basename(d.rstrip("/"))
        with tarfile.open(os.path.join(OUT, f"{name}.tar"), "w") as t:
            t.add(d, arcname=name)
        print("packed", d, os.path.getsize(os.path.join(OUT, f"{name}.tar")) / 1e6, "MB", flush=True)
        dirs[:] = []
