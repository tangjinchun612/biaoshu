import yaml
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel


class Dimension(BaseModel):
    name: str
    description: str
    weight: int


class Prompts(BaseModel):
    extract_requirements: str
    compare_analysis: str


class Scoring(BaseModel):
    status_scores: Dict[str, int]
    pass_threshold: int


class OutputConfig(BaseModel):
    formats: List[str]
    default_format: str
    include_original_text: bool


class AppConfig(BaseModel):
    dimensions: List[Dimension]
    prompts: Prompts
    scoring: Scoring
    output: OutputConfig


def load_config(config_path: str = "config.yaml") -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return AppConfig(**data)


def get_extraction_prompt(config: AppConfig, tender_content: str) -> str:
    return config.prompts.extract_requirements.format(tender_content=tender_content)


def get_comparison_prompt(config: AppConfig, requirement: str, bid_response: str) -> str:
    return config.prompts.compare_analysis.format(
        requirement=requirement,
        bid_response=bid_response
    )
