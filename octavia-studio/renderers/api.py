"""Generic hosted HTTP image-generation backend.

Deliberately provider-neutral. It posts a JSON body to one endpoint and
expects either raw image bytes, a base64 payload, or a URL to fetch. Point it
at whichever hosted service you use by setting the endpoint and the response
shape in config; credentials come from the environment, never from config.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from pipeline.spec import FrameSpec
from renderers.base import Renderer, RenderResult, RendererUnavailable


class APIRenderer(Renderer):
    name = "api"
    capabilities = ["remote"]

    def __init__(self, config: Dict[str, Any], output_dir: pathlib.Path) -> None:
        super().__init__(config, output_dir)
        cfg = config.get("renderer", {}).get("api", {})
        self.endpoint = os.environ.get(cfg.get("endpoint_env", "OCTAVIA_API_ENDPOINT"), "")
        self.api_key = os.environ.get(cfg.get("api_key_env", "OCTAVIA_API_KEY"), "")
        self.model = cfg.get("model", "")
        self.timeout = int(cfg.get("timeout_seconds", 300))
        # Where to find the image in the JSON response, e.g. "data.0.b64_json"
        self.response_path = cfg.get("response_path", "")
        self.response_kind = cfg.get("response_kind", "b64")   # b64 | url | raw

    # ------------------------------------------------------------------
    def preflight(self) -> Dict[str, Any]:
        missing = []
        if not self.endpoint:
            missing.append("endpoint (set OCTAVIA_API_ENDPOINT)")
        if not self.api_key:
            missing.append("api key (set OCTAVIA_API_KEY)")
        if missing:
            raise RendererUnavailable(
                "API backend not configured: missing " + ", ".join(missing) +
                ". Copy .env.example to .env and fill it in."
            )
        return {"backend": "api", "available": True, "endpoint": self.endpoint,
                "model": self.model, "response_kind": self.response_kind}

    # ------------------------------------------------------------------
    def generate_image(self, spec: FrameSpec) -> RenderResult:
        start = time.time()
        payload = {
            "model": self.model,
            "prompt": spec.prompt,
            "negative_prompt": spec.negative_prompt,
            "width": spec.width,
            "height": spec.height,
            "seed": spec.seeds.identity_seed,
            "n": 1,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                body = resp.read()
            dest = self.output_dir / f"{spec.frame_id}.png"

            if self.response_kind == "raw" or ctype.startswith("image/"):
                dest.write_bytes(body)
            else:
                doc = json.loads(body.decode("utf-8"))
                value = self._dig(doc, self.response_path)
                if value is None:
                    return RenderResult(ok=False, backend=self.name,
                                        error=f"Could not locate image at response_path "
                                              f"{self.response_path!r} in response",
                                        duration_seconds=time.time() - start)
                if self.response_kind == "url":
                    with urllib.request.urlopen(value, timeout=120) as img:
                        dest.write_bytes(img.read())
                else:
                    dest.write_bytes(base64.b64decode(value))

            return RenderResult(ok=True, image_path=dest, backend=self.name,
                                duration_seconds=time.time() - start)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            return RenderResult(ok=False, backend=self.name,
                                error=f"HTTP {exc.code}: {detail}",
                                duration_seconds=time.time() - start)
        except Exception as exc:
            return RenderResult(ok=False, backend=self.name,
                                error=f"{type(exc).__name__}: {exc}",
                                duration_seconds=time.time() - start)

    @staticmethod
    def _dig(doc: Any, path: str) -> Optional[Any]:
        if not path:
            return None
        cur = doc
        for part in path.split("."):
            if isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                except (ValueError, IndexError):
                    return None
            elif isinstance(cur, dict):
                if part not in cur:
                    return None
                cur = cur[part]
            else:
                return None
        return cur
