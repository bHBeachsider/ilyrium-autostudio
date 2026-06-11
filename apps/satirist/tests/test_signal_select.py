import satirist
import satirist.config as cfg


def test_package_imports_and_config_defaults():
    assert satirist.__version__ == "0.1.0"
    # defaults exist and are strings
    assert cfg.BRAIN_URL.startswith("http")
    assert cfg.JUDGE_MODEL == "anthropic/claude-sonnet-4.6"
    assert cfg.LORA_S3_URI.endswith("nast_sdxl.safetensors")
