import inspect
import satirist.render as render


def test_render_exposes_callables_with_expected_signatures():
    assert callable(render.render_sdxl)
    assert callable(render.fetch_lora)
    # render_sdxl(image_prompt, out_path, lora_path=None) — image_prompt + out_path required
    params = list(inspect.signature(render.render_sdxl).parameters)
    assert params[:2] == ["image_prompt", "out_path"]
    fp = list(inspect.signature(render.fetch_lora).parameters)
    assert fp[:2] == ["s3_uri", "dest"]


def test_render_flux_exposed_with_expected_signature():
    assert callable(render.render_flux)
    # render_flux(image_prompt, out_path, *, loras, ...)
    params = list(inspect.signature(render.render_flux).parameters)
    assert params[:2] == ["image_prompt", "out_path"]
    assert "loras" in params


def test_render_flux_panels_exposed_for_strips():
    # render_flux_panels(jobs, *, loras, ...) — one pipeline load for many panels
    assert callable(render.render_flux_panels)
    params = list(inspect.signature(render.render_flux_panels).parameters)
    assert params[0] == "jobs"
    assert "loras" in params
