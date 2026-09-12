"""Pure-Python local backend.

The geometry and device logic are pure functions with no torch import, so
they are tested everywhere. The full render chain is exercised against a
tiny randomly-initialised pipeline when torch and diffusers are present —
that proves base -> hires_fix -> face_detail -> upscale actually executes,
without downloading a multi-gigabyte checkpoint.
"""
import pathlib
import sys
import tempfile

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from renderers.base import RendererUnavailable
from renderers.diffusers_local import (MODEL_TIERS, DiffusersRenderer,
                                       estimate_runtime_seconds, face_crop_box,
                                       select_device, snap_to_multiple)
from renderers.registry import available_backends, get_renderer

CFG = yaml.safe_load((ROOT / "config/studio.yaml").read_text())

torch = pytest.importorskip("torch", reason="local backend needs torch")
diffusers = pytest.importorskip("diffusers", reason="local backend needs diffusers")


# ----------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------
def test_snap_rounds_to_multiples_of_eight():
    """UNet latents require /8 dimensions; an unsnapped size crashes deep in
    the model instead of raising something readable."""
    assert snap_to_multiple(1150) == 1152
    assert snap_to_multiple(897) == 896
    assert snap_to_multiple(1024) == 1024
    for n in range(8, 2048, 37):
        assert snap_to_multiple(n) % 8 == 0


def test_snap_never_returns_zero():
    assert snap_to_multiple(1) == 8
    assert snap_to_multiple(0) == 8


def test_select_device_returns_known_pair():
    device, dtype = select_device()
    assert device in ("cuda", "mps", "cpu")
    assert dtype in ("float16", "float32")


def test_explicit_device_is_honoured():
    assert select_device("cpu") == ("cpu", "float32")
    assert select_device("cuda")[0] == "cuda"


def test_cpu_never_uses_fp16():
    """fp16 on CPU is slower than fp32 and unsupported for many ops."""
    assert select_device("cpu")[1] == "float32"


def test_face_crop_scales_with_framing():
    """A close portrait fills the frame with face; an environmental shot
    leaves it small and high."""
    W, H = 896, 1152
    areas = {}
    for em in ("face", "upper_body", "body", "environment"):
        l, t, r, b = face_crop_box(W, H, em)
        areas[em] = (r - l) * (b - t)
    assert areas["face"] > areas["upper_body"] > areas["body"] > areas["environment"]


def test_face_crop_stays_inside_the_image():
    for em in ("face", "upper_body", "body", "environment", "detail", ""):
        for yaw in (-80, -30, 0, 30, 80):
            l, t, r, b = face_crop_box(896, 1152, em, yaw)
            assert 0 <= l < r <= 896
            assert 0 <= t < b <= 1152


def test_face_crop_follows_head_yaw():
    """Yaw is positive toward her right, which is frame-left."""
    left_turn = face_crop_box(896, 1152, "face", -60)
    right_turn = face_crop_box(896, 1152, "face", 60)
    assert left_turn[0] != right_turn[0]


def test_face_crop_sits_in_the_upper_frame():
    _, top, _, bottom = face_crop_box(896, 1152, "body")
    assert (top + bottom) / 2 < 1152 * 0.6, "face region should not be centred low"


def test_runtime_estimate_orders_devices_correctly():
    args = (40, 896, 1152)
    assert (estimate_runtime_seconds("cuda", *args)
            < estimate_runtime_seconds("mps", *args)
            < estimate_runtime_seconds("cpu", *args))


def test_runtime_estimate_scales_with_passes():
    one = estimate_runtime_seconds("cpu", 40, 896, 1152, passes=1)
    three = estimate_runtime_seconds("cpu", 40, 896, 1152, passes=3)
    assert three > one * 2.5


# ----------------------------------------------------------------------
# Registry and preflight
# ----------------------------------------------------------------------
def test_backend_is_registered():
    assert "diffusers" in available_backends()
    with tempfile.TemporaryDirectory() as td:
        assert isinstance(get_renderer("diffusers", CFG, pathlib.Path(td)),
                          DiffusersRenderer)


def test_preflight_refuses_without_a_model():
    with tempfile.TemporaryDirectory() as td:
        r = get_renderer("diffusers", CFG, pathlib.Path(td))
        with pytest.raises(RendererUnavailable, match="model_id"):
            r.preflight()


def test_preflight_refuses_a_missing_local_model():
    import copy
    cfg = copy.deepcopy(CFG)
    cfg["renderer"]["diffusers"]["model_id"] = "nonexistent/model-xyz"
    cfg["renderer"]["diffusers"]["local_files_only"] = True
    with tempfile.TemporaryDirectory() as td:
        r = get_renderer("diffusers", cfg, pathlib.Path(td))
        with pytest.raises(RendererUnavailable, match="not present locally"):
            r.preflight()


def test_backend_declares_its_capabilities():
    """The render plan resolves passes against these, so they must be real."""
    with tempfile.TemporaryDirectory() as td:
        r = get_renderer("diffusers", CFG, pathlib.Path(td))
        for cap in ("hires_fix", "face_restore", "lora", "pure_python"):
            assert r.supports(cap)


def test_render_plan_keeps_all_passes_on_this_backend():
    from pipeline.renderplan import default_plan
    with tempfile.TemporaryDirectory() as td:
        r = get_renderer("diffusers", CFG, pathlib.Path(td))
        plan = default_plan(CFG, 896, 1152).resolve(list(r.capabilities))
        for p in plan.passes:
            if p.enabled:
                assert p.skipped_reason is None, f"{p.name} skipped on a backend that supports it"


def test_model_tiers_cover_every_hardware_tier():
    from scripts.detect_hardware import recommend_models
    for vram, vendor in ((24000, "nvidia"), (16000, "nvidia"), (12000, "nvidia"),
                         (8000, "nvidia"), (0, None)):
        tier = recommend_models({"vram_mb": vram, "vendor": vendor},
                                {"total_mb": 32000}, {"free_gb": 100})["tier"]
        if tier in MODEL_TIERS:
            assert MODEL_TIERS[tier], f"tier {tier} has no recommended checkpoint"


# ----------------------------------------------------------------------
# Full chain against a tiny locally-built pipeline
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def tiny_model(tmp_path_factory):
    """A ~5 MB randomly-initialised SD pipeline. Output is noise; the point
    is that every pass runs and composites."""
    import json

    from diffusers import (AutoencoderKL, PNDMScheduler, StableDiffusionPipeline,
                           UNet2DConditionModel)
    from transformers import CLIPTextConfig, CLIPTextModel, CLIPTokenizer

    root = tmp_path_factory.mktemp("tiny")
    tok_dir = root / "tok"
    tok_dir.mkdir()
    vocab = {"<|startoftext|>": 0, "<|endoftext|>": 1, "!": 2}
    i = 3
    for c in [chr(c) for c in range(97, 123)] + [chr(c) for c in range(48, 58)]:
        vocab[c] = i; i += 1
        vocab[c + "</w>"] = i; i += 1
    (tok_dir / "vocab.json").write_text(json.dumps(vocab))
    (tok_dir / "merges.txt").write_text("#version: 0.2")

    torch.manual_seed(0)
    unet = UNet2DConditionModel(
        block_out_channels=(32, 64), layers_per_block=1, sample_size=32,
        in_channels=4, out_channels=4,
        down_block_types=("DownBlock2D", "CrossAttnDownBlock2D"),
        up_block_types=("CrossAttnUpBlock2D", "UpBlock2D"),
        cross_attention_dim=32, norm_num_groups=8)
    vae = AutoencoderKL(
        block_out_channels=(32,), in_channels=3, out_channels=3,
        down_block_types=("DownEncoderBlock2D",), up_block_types=("UpDecoderBlock2D",),
        latent_channels=4, norm_num_groups=8, sample_size=64)
    text_encoder = CLIPTextModel(CLIPTextConfig(
        bos_token_id=0, eos_token_id=1, hidden_size=32, intermediate_size=37,
        layer_norm_eps=1e-5, num_attention_heads=4, num_hidden_layers=5,
        pad_token_id=1, vocab_size=len(vocab), max_position_embeddings=77))
    # model_max_length is what real checkpoints ship; without it the tokenizer
    # falls back to a sentinel that overflows enable_truncation().
    tokenizer = CLIPTokenizer(str(tok_dir / "vocab.json"), str(tok_dir / "merges.txt"),
                              model_max_length=77)
    dest = root / "tinysd"
    StableDiffusionPipeline(
        vae=vae, text_encoder=text_encoder, tokenizer=tokenizer, unet=unet,
        scheduler=PNDMScheduler(beta_start=0.00085, beta_end=0.012,
                                beta_schedule="scaled_linear", skip_prk_steps=True,
                                steps_offset=1),
        safety_checker=None, feature_extractor=None, image_encoder=None,
        requires_safety_checker=False).save_pretrained(str(dest))
    return dest


def _tiny_cfg(model_dir, **passes):
    import copy
    cfg = copy.deepcopy(CFG)
    cfg["renderer"]["backend"] = "diffusers"
    cfg["renderer"]["diffusers"]["model_path"] = str(model_dir)
    cfg["renderer"]["diffusers"]["local_files_only"] = True
    for name, steps in (("base", 2), ("hires_fix", 2), ("face_detail", 2)):
        cfg["hero"]["passes"][name]["steps"] = steps
    for k, v in passes.items():
        cfg["hero"]["passes"][k].update(v)
    return cfg


def _tiny_spec(cfg):
    from pipeline.compose import Composer
    from pipeline.history import DiversityHistory
    from pipeline.prompt import build_prompts
    from pipeline.sampler import Catalogue, Sampler
    from pipeline.seeds import seed_record
    pol = yaml.safe_load((ROOT / "config/content_policy.yaml").read_text())
    idn = yaml.safe_load((ROOT / "config/identity.yaml").read_text())
    phy = yaml.safe_load((ROOT / "config/physique.yaml").read_text())
    cat = Catalogue()
    smp = Sampler(cat, DiversityHistory(24), cfg, planned_total=1)
    spec = Composer(cat, smp, cfg, pol).compose("TINY", 0, seed_record(42, "TINY", 0))
    spec.prompt, spec.negative_prompt = build_prompts(
        spec, idn, phy, pol, cat, cfg["identity"], {"tier": "compact"})
    spec.width, spec.height = 128, 160
    return spec


@pytest.mark.slow
def test_full_multipass_chain_executes(tiny_model, tmp_path):
    cfg = _tiny_cfg(tiny_model)
    spec = _tiny_spec(cfg)
    r = get_renderer("diffusers", cfg, tmp_path / "out")
    r.preflight()
    result = r.generate_image(spec)
    r.close()
    assert result.ok, result.error
    assert result.metadata["passes_executed"] == ["base", "hires_fix", "face_detail"]
    assert result.image_path.is_file()


@pytest.mark.slow
def test_hires_pass_enlarges_the_image(tiny_model, tmp_path):
    cfg = _tiny_cfg(tiny_model, face_detail={"enabled": False})
    spec = _tiny_spec(cfg)
    r = get_renderer("diffusers", cfg, tmp_path / "out2")
    r.preflight()
    result = r.generate_image(spec)
    r.close()
    assert result.ok, result.error
    w, h = result.metadata["final_size"]
    assert w > spec.width and h > spec.height


@pytest.mark.slow
def test_disabling_passes_is_honoured(tiny_model, tmp_path):
    cfg = _tiny_cfg(tiny_model, hires_fix={"enabled": False},
                    face_detail={"enabled": False})
    spec = _tiny_spec(cfg)
    r = get_renderer("diffusers", cfg, tmp_path / "out3")
    r.preflight()
    result = r.generate_image(spec)
    r.close()
    assert result.ok, result.error
    assert result.metadata["passes_executed"] == ["base"]
    assert result.metadata["final_size"] == [spec.width, spec.height]


@pytest.mark.slow
def test_same_seed_reproduces_the_same_image(tiny_model, tmp_path):
    """Reproducibility has to survive the renderer, not just the sampler."""
    import hashlib
    cfg = _tiny_cfg(tiny_model, hires_fix={"enabled": False},
                    face_detail={"enabled": False})
    digests = []
    for i in range(2):
        spec = _tiny_spec(cfg)
        r = get_renderer("diffusers", cfg, tmp_path / f"rep{i}")
        r.preflight()
        result = r.generate_image(spec)
        r.close()
        assert result.ok, result.error
        digests.append(hashlib.sha256(result.image_path.read_bytes()).hexdigest())
    assert digests[0] == digests[1], "same seed produced different pixels"


@pytest.mark.slow
def test_render_failure_returns_cleanly(tiny_model, tmp_path):
    """A failure must not raise — the run has to continue to the next frame."""
    cfg = _tiny_cfg(tiny_model)
    spec = _tiny_spec(cfg)
    spec.prompt = None          # force a failure inside the pipeline
    r = get_renderer("diffusers", cfg, tmp_path / "bad")
    r.preflight()
    result = r.generate_image(spec)
    r.close()
    assert result.ok is False
    assert result.error
