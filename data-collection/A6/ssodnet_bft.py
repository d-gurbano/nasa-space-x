"""A6 (partner, France/IMCCE): read only the needed columns of SsODNet ssoBFT (best-estimate table) via HTTP Range
requests, so we do not store the full 856 MB parquet. Value for Rewind: ~1.5M asteroids with a best-estimate
taxonomy (from spectra, SDSS/Gaia colors), diameter, albedo and spin -> many more labeled answers for validation.
usage: python code/A6/ssodnet_bft.py"""
import sys, os, hashlib, csv, datetime
sys.path.insert(0, os.path.dirname(__file__)); from httpfile import HTTPFile
import pyarrow.parquet as pq
URL = "https://ssp.imcce.fr/data/ssoBFT-latest_Asteroid.parquet"
COLS = ["id", "number", "name", "class", "diameter.value", "diameter.error.min", "diameter.error.max", "albedo.value",
        "albedo.error.min", "albedo.error.max", "taxonomy.class", "taxonomy.complex", "taxonomy.waverange",
        "taxonomy.scheme", "taxonomy.technique", "spins.period.value", "spins.period_flag", "density.value"]
f = HTTPFile(URL); pf = pq.ParquetFile(f)
import time; t0 = time.time()
t = pf.read(columns=COLS)
print("read s", time.time() - t0, flush=True)
out = "data/06-composition/raw/ssodnet/ssoBFT_Asteroid_selected_columns.parquet"; os.makedirs(os.path.dirname(out), exist_ok=True)
pq.write_table(t, out, compression="zstd")
print(t.num_rows, "rows; bytes fetched", f.nbytes, "of", f.size)
b = open(out, "rb").read()
with open("data/06-composition/manifest.csv", "a", newline="") as m:
    csv.writer(m).writerow([out.replace("data/06-composition/", ""), URL + " (columns subset via HTTP Range)", len(b),
                            hashlib.sha256(b).hexdigest(), datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%MZ")])
