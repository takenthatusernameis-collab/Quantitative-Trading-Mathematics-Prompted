import os, tempfile
from pathlib import Path
from qtr.utils import config

d = tempfile.mkdtemp()
os.chdir(d)
config.reset_config()
os.environ["QTR_CACHE_DIR"] = "10"
try:
    cfg = config.load_config()
    print("cfg data.cache_dir =", repr(cfg.get("data", {}).get("cache_dir")))
    from qtr.data.fetcher import DataCache
    dc = DataCache()
    print("cache_dir =", dc.cache_dir)
except Exception as e:
    print("CRASH:", type(e).__name__, e)