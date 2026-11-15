"""Minimal seekable read-only HTTP file (Range requests) so pyarrow can read selected parquet columns remotely."""
import io, requests
class HTTPFile(io.RawIOBase):
    def __init__(self, url, block=256 * 2**10):
        self.url, self.pos, self.block, self.cache = url, 0, block, {}
        r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=60); self.size = int(r.headers["content-range"].split("/")[-1]); self.nbytes = 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off); return self.pos
    def _get(self, s, e):
        import time
        for k in range(5):
            try:
                r = requests.get(self.url, headers={"Range": f"bytes={s}-{e}"}, timeout=600); r.raise_for_status()
                self.nbytes += len(r.content); return r.content
            except Exception:
                time.sleep(5 * (k + 1))
        raise IOError("range read failed")
    def _blk(self, i):
        if i not in self.cache:
            s = i * self.block; e = min(self.size, s + self.block) - 1
            for k in range(5):
                try:
                    r = requests.get(self.url, headers={"Range": f"bytes={s}-{e}"}, timeout=120); r.raise_for_status(); break
                except Exception:
                    import time; time.sleep(5 * (k + 1))
            self.cache[i] = r.content; self.nbytes += len(r.content)
        return self.cache[i]
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos)); out = bytearray()
        if n >= 65536:  # large read (a parquet column chunk): fetch exactly this range, no block rounding
            out = self._get(self.pos, self.pos + n - 1); self.pos += len(out); return out
        while len(out) < n:
            i, o = divmod(self.pos, self.block); b = self._blk(i)[o:o + n - len(out)]
            out += b; self.pos += len(b)
        return bytes(out)
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)
