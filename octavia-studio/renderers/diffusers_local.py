"""Pure-Python local render backend built on `diffusers`.

No external server, no hosted API: this loads a checkpoint into the current
Python process and runs the full multi-pass chain in-process.

    base          txt2img at the working resolution
    hires_fix     img2img resample of an upscaled base, low denoise
    face_detail   crop the face region, resample at full resolution,
                  composite back with a feathered mask
    upscale       final Lanczos or model-based enlargement

WHY THE DENOISE VALUES ARE LOW
------------------------------
Each refinement pass re-runs the sampler over an existing image. The higher
the denoise, the more freedom it has to redraw — including redrawing the
face. Above roughly 0.5 the face detail pass stops refining Octavia and
starts inventing a different woman, which defeats the entire identity
system. 0.40 for hires and 0.30 for face detail add real detail while
holding the likeness.

MODEL WEIGHTS ARE NOT DOWNLOADED AUTOMATICALLY
----------------------------------------------
`preflight()` reports what is missing and what it would cost. Fetching is an
explicit, separate step (`scripts/fetch_models.py`) because a checkpoint is
2-7 GB and that is the operator's decision, not the studio's.
"""
from __future__ import annotations

import os
import pathlib
import time
from typing import Any, Dict, List, Optional, Tuple

from pipeline.spec import FrameSpec
from renderers.base import Renderer, RenderResult, RendererUnavailable

# Recommended checkpoints by hardware tier. Chosen so the studio can advise
# without ever fetching anything on its own.
MODEL_TIERS = {
    "high": [("stabilityai/stable-diffusion-xl-base-1.0", 6.9),
             ("black-forest-labs/FLUX.1-dev", 23.8)],
    "good": [("stabilityai/stable-diffusion-xl-base-1.0", 6.9)],
    "moderate": [("stabilityai/stable-diffusion-xl-base-1.0", 6.9)],
    "low": [("runwayml/stable-diffusion-v1-5", 4.3)],
    "cpu_only": [("runwayml/stable-diffusion-v1-5", 4.3)],
}


# ----------------------------------------------------------------------
# Pure helpers — no torch import, so they are testable anywhere.
# ----------------------------------------------------------------------
def select_device(prefer: str = "auto") -> Tuple[str, str]:
    """Return (device, dtype_name). Kept importable without torch."""
    if prefer and prefer != "auto":
        return prefer, ("float32" if prefer == "cpu" else "float16")
    try:
        import torch
    except ImportError:
        return "cpu", "float32"
    if torch.cuda.is_available():
        return "cuda", "float16"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        # fp16 on MPS is unreliable for VAE decode; fp32 is the safe default.
        return "mps", "float32"
    return "cpu", "float32"


def snap_to_multiple(value: int, multiple: int = 8) -> int:
    """UNet latents require dimensions divisible by 8. Passing an unsnapped
    size produces a shape-mismatch crash deep in the model rather than a
    readable error, so snap before it ever reaches the pipeline."""
    return max(multiple, int(round(value / multiple)) * multiple)


def face_crop_box(width: int, height: int, shot_emphasis: str,
                  head_yaw: float = 0.0) -> Tuple[int, int, int, int]:
    """Estimate the face region for the detail pass.

    A real face detector is better, and `FaceDetailPass` uses one when
    available. This geometric fallback exists because the alternative —
    skipping the detail pass when no detector is installed — throws away the
    single largest quality gain in portraiture. The estimate follows the
    framing: a close portrait puts the face across most of the frame, an
    environmental shot puts it small and high.
    """
    frac = {
        "face": 0.62,
        "upper_body": 0.42,
        "body": 0.26,
        "environment": 0.16,
        "detail": 0.45,
    }.get(shot_emphasis, 0.35)

    box_w = int(width * frac)
    box_h = int(height * frac * 0.82)

    # Subjects are conventionally framed with the head in the upper third.
    centre_y = int(height * (0.30 if frac < 0.5 else 0.38))
    # A turned head sits off the vertical centre line, toward the direction
    # of the turn; yaw is positive toward her right, which is frame-left.
    centre_x = int(width * 0.5 - (head_yaw / 90.0) * width * 0.10)

    left = max(0, centre_x - box_w // 2)
    top = max(0, centre_y - box_h // 2)
    right = min(width, left + box_w)
    bottom = min(height, top + box_h)
    # Re-anchor if clamping shrank the box against an edge.
    left = max(0, right - box_w)
    top = max(0, bottom - box_h)
    return left, top, right, bottom


def estimate_runtime_seconds(device: str, steps: int, width: int, height: int,
                             passes: int = 1) -> float:
    """Rough wall-clock estimate, so a CPU run reports minutes up front
    instead of appearing to hang."""
    megapixels = (width * height) / 1_000_000
    per_step = {"cuda": 0.055, "mps": 0.55, "cpu": 6.0}.get(device, 6.0)
    return per_step * steps * max(0.35, megapixels) * passes


# ----------------------------------------------------------------------
class DiffusersRenderer(Renderer):
    name = "diffusers"

    def __init__(self, config: Dict[str, Any], output_dir: pathlib.Path) -> None:
        super().__init__(config, output_dir)
        cfg = config.get("renderer", {}).get("diffusers", {})
        self.model_id = cfg.get("model_id", "")
        self.model_path = cfg.get("model_path", "")
        self.device_pref = cfg.get("device", "auto")
        self.local_files_only = bool(cfg.get("local_files_only", True))
        self.enable_attention_slicing = bool(cfg.get("attention_slicing", True))
        self.enable_vae_slicing = bool(cfg.get("vae_slicing", True))
        self.offload = bool(cfg.get("cpu_offload", False))
        self.hero_cfg = config.get("hero", {})
        self.identity_cfg = config.get("identity", {})
        self._pipe = None
        self._img2img = None
        if self.local_files_only:
            # `local_files_only=True` on the pipeline call is not enough: the
            # hub client still attempts metadata lookups and retries hard when
            # they fail. On an air-gapped or policy-restricted machine that
            # turns a local render into a long stall against a host it was
            # never going to reach. Make offline the actual process state.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        self.device, self.dtype_name = select_device(self.device_pref)
        self.capabilities = ["hires_fix", "face_restore", "upscale", "lora",
                             "local", "pure_python"]

    # ------------------------------------------------------------------
    def preflight(self) -> Dict[str, Any]:
        missing: List[str] = []
        try:
            import torch  # noqa: F401
        except ImportError:
            missing.append("torch")
        try:
            import diffusers  # noqa: F401
        except ImportError:
            missing.append("diffusers")
        try:
            import transformers  # noqa: F401
        except ImportError:
            missing.append("transformers")

        if missing:
            raise RendererUnavailable(
                "Pure-Python backend needs " + ", ".join(missing) +
                ". Install with:  pip install -r requirements-local.txt")

        source = self.model_path or self.model_id
        if not source:
            raise RendererUnavailable(
                "No renderer.diffusers.model_id or model_path configured. "
                "Run `python scripts/fetch_models.py --list` to see recommendations "
                "for this machine.")

        resolved = pathlib.Path(source)
        have_local = resolved.exists()
        if not have_local and self.local_files_only:
            from_cache = _in_hf_cache(source)
            if not from_cache:
                raise RendererUnavailable(
                    f"Model {source!r} is not present locally and local_files_only "
                    f"is set. Fetch it first:  python scripts/fetch_models.py "
                    f"--model {source}")

        import torch
        info: Dict[str, Any] = {
            "backend": "diffusers",
            "available": True,
            "pure_python": True,
            "device": self.device,
            "dtype": self.dtype_name,
            "model": source,
            "model_local": have_local or _in_hf_cache(source),
            "torch": torch.__version__,
            "capabilities": {c: True for c in self.capabilities},
        }
        if self.device == "cuda":
            info["vram_total_bytes"] = torch.cuda.get_device_properties(0).total_memory
            info["gpu_name"] = torch.cuda.get_device_name(0)
        base = self.hero_cfg.get("passes", {}).get("base", {})
        info["estimated_seconds_per_pass"] = round(estimate_runtime_seconds(
            self.device, int(base.get("steps", 40)),
            int(self.config.get("output", {}).get("width", 896)),
            int(self.config.get("output", {}).get("height", 1152))), 1)
        if self.device == "cpu":
            info["warning"] = (
                "Running on CPU. Expect minutes per pass, not seconds. "
                "Reduce steps and resolution, or use a CUDA/MPS machine.")
        return info

    # ------------------------------------------------------------------
    def _load(self):
        if self._pipe is not None:
            return self._pipe
        import torch
        from diffusers import AutoPipelineForText2Image

        dtype = getattr(torch, self.dtype_name)
        source = self.model_path or self.model_id
        # diffusers renamed `torch_dtype` to `dtype` (deprecated for removal
        # in 1.0.0). Prefer the new spelling and fall back for older installs,
        # so the backend works across the versions people actually have.
        kwargs = dict(use_safetensors=True, local_files_only=self.local_files_only)
        try:
            pipe = AutoPipelineForText2Image.from_pretrained(source, dtype=dtype, **kwargs)
        except TypeError:
            pipe = AutoPipelineForText2Image.from_pretrained(
                source, torch_dtype=dtype, **kwargs)

        lora = self.identity_cfg.get("lora", {}) or {}
        if lora.get("enabled") and lora.get("name"):
            # The trained Octavia adapter. Without it, identity is asserted by
            # prompt text alone and will drift across a series.
            pipe.load_lora_weights(lora["name"])
            try:
                pipe.fuse_lora(lora_scale=float(lora.get("strength_model", 0.85)))
            except Exception:
                pass

        if self.offload and self.device == "cuda":
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(self.device)
        if self.enable_attention_slicing:
            pipe.enable_attention_slicing()
        if self.enable_vae_slicing and hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
        pipe.set_progress_bar_config(disable=True)
        self._pipe = pipe
        return pipe

    def _img2img_pipe(self):
        if self._img2img is None:
            from diffusers import AutoPipelineForImage2Image
            self._img2img = AutoPipelineForImage2Image.from_pipe(self._load())
            self._img2img.set_progress_bar_config(disable=True)
        return self._img2img

    # ------------------------------------------------------------------
    def generate_image(self, spec: FrameSpec) -> RenderResult:
        start = time.time()
        try:
            import torch
            from PIL import Image

            pipe = self._load()
            passes = self.hero_cfg.get("passes", {})
            base_cfg = passes.get("base", {})

            width = snap_to_multiple(spec.width)
            height = snap_to_multiple(spec.height)
            generator = torch.Generator(
                device="cpu" if self.device == "mps" else self.device
            ).manual_seed(int(spec.seeds.identity_seed))

            executed: List[str] = []
            image = pipe(
                prompt=spec.prompt,
                negative_prompt=spec.negative_prompt,
                width=width, height=height,
                num_inference_steps=int(base_cfg.get("steps", 40)),
                guidance_scale=float(base_cfg.get("cfg_scale", 5.0)),
                generator=generator,
            ).images[0]
            executed.append("base")

            hires = passes.get("hires_fix", {})
            if hires.get("enabled", True):
                scale = float(hires.get("scale", 1.5))
                up = image.resize((snap_to_multiple(int(width * scale)),
                                   snap_to_multiple(int(height * scale))),
                                  Image.Resampling.LANCZOS)
                image = self._img2img_pipe()(
                    prompt=spec.prompt,
                    negative_prompt=spec.negative_prompt,
                    image=up,
                    strength=float(hires.get("denoise", 0.40)),
                    num_inference_steps=int(hires.get("steps", 20)),
                    guidance_scale=float(base_cfg.get("cfg_scale", 5.0)),
                    generator=generator,
                ).images[0]
                executed.append("hires_fix")

            face = passes.get("face_detail", {})
            if face.get("enabled", True):
                image = self._face_pass(image, spec, face, generator)
                executed.append("face_detail")

            upscale = passes.get("upscale", {})
            if upscale.get("enabled", False):
                s = float(upscale.get("scale", 2.0))
                image = image.resize((int(image.width * s), int(image.height * s)),
                                     Image.Resampling.LANCZOS)
                executed.append("upscale")

            dest = self.output_dir / f"{spec.frame_id}.png"
            image.save(dest, "PNG")
            return RenderResult(
                ok=True, image_path=dest, backend=self.name,
                duration_seconds=time.time() - start,
                metadata={"device": self.device, "dtype": self.dtype_name,
                          "passes_executed": executed,
                          "final_size": [image.width, image.height]},
            )
        except Exception as exc:
            return RenderResult(ok=False, backend=self.name,
                                error=f"{type(exc).__name__}: {exc}",
                                duration_seconds=time.time() - start)

    # ------------------------------------------------------------------
    def _face_pass(self, image, spec: FrameSpec, face_cfg: Dict[str, Any], generator):
        """Resample the face at full resolution and composite it back.

        The face occupies a small share of the base sample's pixels, so it is
        rendered with correspondingly little detail. Re-running the sampler on
        a full-resolution crop is the largest single quality gain available
        for portraiture.
        """
        from PIL import Image, ImageFilter

        emphasis = (spec.camera.get("shot", {}) or {}).get("emphasis", "")
        box = face_crop_box(image.width, image.height, emphasis, spec.head.yaw)
        pad = int(face_cfg.get("padding", 32))
        left = max(0, box[0] - pad)
        top = max(0, box[1] - pad)
        right = min(image.width, box[2] + pad)
        bottom = min(image.height, box[3] + pad)
        if right - left < 64 or bottom - top < 64:
            return image

        crop = image.crop((left, top, right, bottom))
        target = (snap_to_multiple(crop.width), snap_to_multiple(crop.height))
        work = crop.resize(target, Image.Resampling.LANCZOS)

        refined = self._img2img_pipe()(
            prompt=spec.prompt,
            negative_prompt=spec.negative_prompt,
            image=work,
            strength=float(face_cfg.get("denoise", 0.30)),
            num_inference_steps=int(face_cfg.get("steps", 20)),
            generator=generator,
        ).images[0].resize(crop.size, Image.Resampling.LANCZOS)

        # Feathered mask so the refined crop blends rather than showing a seam.
        feather = max(1, int(face_cfg.get("feather", 8)))
        mask = Image.new("L", crop.size, 0)
        inner = Image.new("L", (max(1, crop.width - feather * 2),
                                max(1, crop.height - feather * 2)), 255)
        mask.paste(inner, (feather, feather))
        mask = mask.filter(ImageFilter.GaussianBlur(feather))

        out = image.copy()
        out.paste(refined, (left, top), mask)
        return out

    def close(self) -> None:
        self._pipe = None
        self._img2img = None
        try:
            import torch
            if self.device == "cuda":
                torch.cuda.empty_cache()
        except Exception:
            pass


def _in_hf_cache(model_id: str) -> bool:
    cache = pathlib.Path(os.environ.get("HF_HOME", pathlib.Path.home() / ".cache/huggingface"))
    hub = cache / "hub"
    if not hub.is_dir():
        return False
    slug = "models--" + model_id.replace("/", "--")
    return (hub / slug).is_dir()
