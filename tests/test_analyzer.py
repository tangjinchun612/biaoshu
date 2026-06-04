import pytest
from core.config import (
    AppConfig,
    get_comparison_prompt,
    get_extraction_prompt,
    load_config,
)


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


def test_config_prompt_formatting():
    config = load_config()

    extraction_prompt = get_extraction_prompt(config, "招标正文测试")
    comparison_prompt = get_comparison_prompt(config, "要求测试", "响应测试")

    assert "<标书文档>\n招标正文测试\n</标书文档>" in extraction_prompt
    assert "{tender_content}" not in extraction_prompt
    assert "要求测试" in comparison_prompt
    assert "响应测试" in comparison_prompt
