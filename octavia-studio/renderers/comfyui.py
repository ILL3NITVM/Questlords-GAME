"""ComfyUI backend.

Talks to a local or remote ComfyUI server over its HTTP API. The studio never
ships a workflow graph of its own — you point it at a workflow JSON exported
from the ComfyUI UI, and this adapter injects the prompt, seed and dimensions
into nodes you nominate in config/studio.yaml.

That indirection is deliberate: workflows differ wildly between model families
(SDXL vs Flux vs SD3), and hard-coding one would make the adapter obsolete the
moment you change checkpoints.

Capability probing (section 15): ``preflight()`` reports which optional nodes
the server actually has — IPAdapter / InstantID for reference conditioning,
ControlNet for pose, LoRA loaders, upscalers, face restoration. The studio
degrades gracefully when a capability is absent rather than failing.
"""
from __future__ import annotations

import copy
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

from pipeline.spec import FrameSpec
from renderers.base import Renderer, RenderResult, RendererUnavailable

# Node class names we look for when reporting capabilities.
CAPABILITY_NODES = {
    "reference_ipadapter": ["IPAdapterAdvanced", "IPAdapter", "IPAdapterApply"],
    "reference_instantid": ["InstantIDModelLoader", "ApplyInstantID"],
    "reference_pulid": ["PuLIDModelLoader", "ApplyPulid"],
    "controlnet": ["ControlNetLoader", "ControlNetApplyAdvanced"],
    "openpose": ["OpenposePreprocessor", "DWPreprocessor"],
    "lora": ["LoraLoader", "LoraLoaderModelOnly"],
    "upscale": ["UpscaleModelLoader", "ImageUpscaleWithModel"],
    "face_restore": ["FaceRestoreCFWithModel", "ReActorFaceSwap", "FaceDetailer"],
}


class ComfyUIRenderer(Renderer):
    name = "comfyui"

    def __init__(self, config: Dict[str, Any], output_dir: pathlib.Path) -> None:
        super().__init__(config, output_dir)
        cfg = config.get("renderer", {}).get("comfyui", {})
        self.host = cfg.get("host", "127.0.0.1")
        self.port = int(cfg.get("port", 8188))
        self.timeout = int(cfg.get("timeout_seconds", 600))
        self.base = f"http://{self.host}:{self.port}"
        self.client_id = str(uuid.uuid4())
        self.workflow_path = cfg.get("workflow_template")
        self.node_map: Dict[str, Any] = cfg.get("node_map", {})
        self.lora: Dict[str, Any] = config.get("identity", {}).get("lora", {}) or {}
        self._workflow: Optional[Dict[str, Any]] = None
        self.capabilities: List[str] = []

    # ------------------------------------------------------------------
    def _get(self, route: str, timeout: int = 10) -> Any:
        url = f"{self.base}{route}"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, route: str, payload: Dict[str, Any], timeout: int = 30) -> Any:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base}{route}", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ------------------------------------------------------------------
    def preflight(self) -> Dict[str, Any]:
        try:
            stats = self._get("/system_stats")
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise RendererUnavailable(
                f"ComfyUI not reachable at {self.base} ({exc}). "
                "Start ComfyUI, or set renderer.backend to 'mock' / 'api'."
            ) from exc

        try:
            node_info = self._get("/object_info", timeout=30)
        except Exception:
            node_info = {}

        found: Dict[str, bool] = {}
        for cap, candidates in CAPABILITY_NODES.items():
            present = any(c in node_info for c in candidates)
            found[cap] = present
            if present:
                self.capabilities.append(cap)

        checkpoints: List[str] = []
        ckpt = node_info.get("CheckpointLoaderSimple", {})
        try:
            checkpoints = ckpt["input"]["required"]["ckpt_name"][0]
        except (KeyError, IndexError, TypeError):
            pass

        workflow_ok = bool(self.workflow_path) and pathlib.Path(self.workflow_path).is_file()

        devices = stats.get("devices", [])
        vram = devices[0].get("vram_total") if devices else None

        return {
            "backend": "comfyui",
            "available": True,
            "endpoint": self.base,
            "vram_total_bytes": vram,
            "checkpoints_installed": checkpoints,
            "capabilities": found,
            "workflow_template": self.workflow_path,
            "workflow_present": workflow_ok,
            "node_map_configured": bool(self.node_map),
            "ready": workflow_ok and bool(self.node_map) and bool(checkpoints),
        }

    # ------------------------------------------------------------------
    def _load_workflow(self) -> Dict[str, Any]:
        if self._workflow is None:
            if not self.workflow_path:
                raise RendererUnavailable(
                    "No renderer.comfyui.workflow_template configured. Export a "
                    "workflow from ComfyUI (Save API Format) and point config at it."
                )
            p = pathlib.Path(self.workflow_path)
            if not p.is_file():
                raise RendererUnavailable(f"Workflow template not found: {p}")
            self._workflow = json.loads(p.read_text(encoding="utf-8"))
        return copy.deepcopy(self._workflow)

    def _inject(self, wf: Dict[str, Any], spec: FrameSpec) -> Dict[str, Any]:
        """Write this frame's values into the nodes named by ``node_map``.

        Expected node_map shape::

            node_map:
              positive: {node: "6",  field: "text"}
              negative: {node: "7",  field: "text"}
              seed:     {node: "3",  field: "seed"}
              width:    {node: "5",  field: "width"}
              height:   {node: "5",  field: "height"}
              lora_name:            {node: "10", field: "lora_name"}
              lora_strength_model:  {node: "10", field: "strength_model"}
              lora_strength_clip:   {node: "10", field: "strength_clip"}
        """
        values = {
            "positive": spec.prompt,
            "negative": spec.negative_prompt,
            "seed": spec.seeds.identity_seed,
            "width": spec.width,
            "height": spec.height,
        }
        # A trained identity LoRA, when one is configured. The workflow must
        # already contain a LoraLoader node; node_map names its fields.
        if self.lora.get("enabled"):
            values.update({
                "lora_name": self.lora.get("name", ""),
                "lora_strength_model": float(self.lora.get("strength_model", 0.85)),
                "lora_strength_clip": float(self.lora.get("strength_clip", 0.85)),
            })
        for key, target in self.node_map.items():
            if key not in values or not isinstance(target, dict):
                continue
            node_id, field = str(target.get("node")), target.get("field")
            if node_id in wf and field:
                wf[node_id].setdefault("inputs", {})[field] = values[key]
        return wf

    # ------------------------------------------------------------------
    def generate_image(self, spec: FrameSpec) -> RenderResult:
        start = time.time()
        try:
            wf = self._inject(self._load_workflow(), spec)
            queued = self._post("/prompt", {"prompt": wf, "client_id": self.client_id})
            prompt_id = queued.get("prompt_id")
            if not prompt_id:
                return RenderResult(ok=False, backend=self.name,
                                    error=f"ComfyUI rejected the workflow: {queued}",
                                    duration_seconds=time.time() - start)

            image_ref = self._await_result(prompt_id, start)
            if image_ref is None:
                return RenderResult(ok=False, backend=self.name,
                                    error=f"Timed out after {self.timeout}s waiting for {prompt_id}",
                                    duration_seconds=time.time() - start)

            path = self._download(image_ref, spec)
            return RenderResult(ok=True, image_path=path, backend=self.name,
                                duration_seconds=time.time() - start,
                                metadata={"prompt_id": prompt_id, "comfy_image": image_ref})
        except RendererUnavailable:
            raise
        except Exception as exc:
            return RenderResult(ok=False, backend=self.name,
                                error=f"{type(exc).__name__}: {exc}",
                                duration_seconds=time.time() - start)

    def _await_result(self, prompt_id: str, start: float) -> Optional[Dict[str, Any]]:
        while time.time() - start < self.timeout:
            try:
                history = self._get(f"/history/{prompt_id}")
            except Exception:
                time.sleep(1.5)
                continue
            entry = history.get(prompt_id)
            if entry:
                for node_output in entry.get("outputs", {}).values():
                    for img in node_output.get("images", []):
                        return img
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI execution error: {status}")
            time.sleep(1.5)
        return None

    def _download(self, image_ref: Dict[str, Any], spec: FrameSpec) -> pathlib.Path:
        q = urllib.parse.urlencode({
            "filename": image_ref.get("filename", ""),
            "subfolder": image_ref.get("subfolder", ""),
            "type": image_ref.get("type", "output"),
        })
        dest = self.output_dir / f"{spec.frame_id}.png"
        with urllib.request.urlopen(f"{self.base}/view?{q}", timeout=120) as resp:
            dest.write_bytes(resp.read())
        return dest
