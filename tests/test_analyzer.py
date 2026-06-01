import pytest
from core.config import load_config, AppConfig


def test_load_config():
    config = load_config()
    assert isinstance(config, AppConfig)
    assert len(config.dimensions) == 3
    assert "资质要求" in [d.name for d in config.dimensions]


def test_config_dimensions():
    config = load_config()
    total_weight = sum(d.weight for d in config.dimensions)
    assert total_weight == 100


def test_config_prompts():
    config = load_config()
    assert "{tender_content}" in config.prompts.extract_requirements
    assert "{requirement}" in config.prompts.compare_analysis
    assert "{bid_response}" in config.prompts.compare_analysis
