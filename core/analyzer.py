import json
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from core.config import AppConfig, load_config, get_extraction_prompt, get_comparison_prompt
from core.llm_client import LLMClient
from retriever import LawRetriever
from doc_processor import process_document


class Analyzer:
    def __init__(self, config: Optional[AppConfig] = None, model_key: str = "qwen-plus"):
        self.config = config or load_config()
        self.llm = LLMClient(model_key)
        self.retriever = LawRetriever()
    
    def analyze(self, task_id: str, tender_file_path: str, bid_file_path: str, 
                progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        # 1. 解析文档
        if progress_callback:
            progress_callback(10)
        
        tender_chunks = self._process_file(tender_file_path)
        bid_chunks = self._process_file(bid_file_path)
        
        # 2. 索引文档
        if progress_callback:
            progress_callback(20)
        
        self.retriever.index_doc(tender_chunks, doc_type="tender")
        self.retriever.index_doc(bid_chunks, doc_type="bid")
        
        # 3. 提取招标要求
        if progress_callback:
            progress_callback(30)
        
        requirements = self._extract_requirements(tender_chunks)
        
        # 4. 逐项对比分析
        if progress_callback:
            progress_callback(40)
        
        analyses = []
        total_requirements = len(requirements)
        
        for idx, req in enumerate(requirements):
            progress = 40 + int(50 * (idx + 1) / total_requirements)
            if progress_callback:
                progress_callback(progress)
            
            bid_response_chunks = self.retriever.retrieve(
                req["requirement"], 
                top_k=3, 
                doc_type="bid"
            )
            bid_response_text = "\n".join([chunk["text"] for chunk in bid_response_chunks])
            
            analysis = self._compare_requirement(req, bid_response_text)
            
            analyses.append({
                "requirement": req,
                "analysis": analysis,
                "bid_response_text": bid_response_text
            })
        
        # 5. 生成报告
        if progress_callback:
            progress_callback(95)
        
        result = self._generate_result(task_id, analyses)
        
        if progress_callback:
            progress_callback(100)
        
        return result
    
    def _process_file(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        filename = Path(file_path).name
        return process_document(file_bytes, filename)
    
    def _extract_requirements(self, tender_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tender_content = "\n\n".join([chunk["text"] for chunk in tender_chunks])
        prompt = get_extraction_prompt(self.config, tender_content)
        messages = [{"role": "user", "content": prompt}]
        return self.llm.call_json(messages, max_tokens=16384)
    
    def _compare_requirement(self, requirement: Dict[str, Any], bid_response: str) -> Dict[str, Any]:
        prompt = get_comparison_prompt(self.config, requirement["requirement"], bid_response)
        messages = [{"role": "user", "content": prompt}]
        return self.llm.call_json(messages)
    
    def _generate_result(self, task_id: str, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues_count = sum(len(a["analysis"].get("issues", [])) for a in analyses)
        score = self._calculate_score(analyses)
        
        return {
            "task_id": task_id,
            "requirements_count": len(analyses),
            "issues_count": issues_count,
            "score": score,
            "analyses": analyses
        }
    
    def _calculate_score(self, analyses: List[Dict[str, Any]]) -> float:
        if not analyses:
            return 100.0
        
        total_deduction = 0
        severity_weights = self.config.scoring.severity_weights
        
        for a in analyses:
            severity = a["analysis"].get("severity", "轻微")
            weight = severity_weights.get(severity, 2)
            status = a["analysis"].get("status", "符合")
            
            if status == "不符合":
                total_deduction += weight
            elif status == "部分符合":
                total_deduction += weight * 0.5
        
        score = max(0, 100 - total_deduction)
        return round(score, 2)
