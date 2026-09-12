import os
import pathlib
import sys

# The HuggingFace stack attempts hub lookups even for fully local models and
# retries hard on failure. On a restricted network that turns a 3-second test
# run into thousands of blocked connections and a timeout. Tests are offline
# by construction.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
