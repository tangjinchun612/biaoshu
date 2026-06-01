import json
import base64
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


class ReportGenerator:
    def generate(self, result: Dict[str, Any], format: str = "json") -> Any:
        if format == "json":
            return self.generate_json(result)
        elif format == "markdown":
            return self.generate_markdown(result)
        elif format == "word":
            return self.generate_word(result)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def generate_json(self, result: Dict[str, Any]) -> str:
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def generate_markdown(self, result: Dict[str, Any]) -> str:
        lines = []
        lines.append("# 标书对比分析报告\n")
        lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**任务ID:** {result['task_id']}\n")
        
        lines.append("## 分析概览\n")
        lines.append(f"- **需求数量:** {result['requirements_count']}")
        lines.append(f"- **问题数量:** {result['issues_count']}")
        lines.append(f"- **综合得分:** {result['score']}分\n")
        
        lines.append("## 详细分析\n")
        
        for idx, analysis in enumerate(result['analyses'], 1):
            req = analysis['requirement']
            result_item = analysis['analysis']
            
            lines.append(f"### {idx}. {req['category']} - {req['requirement'][:50]}...\n")
            lines.append(f"**位置:** {req['location']}")
            lines.append(f"**是否强制:** {'是' if req['is_mandatory'] else '否'}\n")
            
            status = result_item.get('status', '未知')
            severity = result_item.get('severity', '未知')
            
            if status == '符合':
                lines.append(f"✅ **状态:** {status}")
            elif status == '部分符合':
                lines.append(f"⚠️ **状态:** {status}")
            else:
                lines.append(f"❌ **状态:** {status}")
            
            lines.append(f"**严重程度:** {severity}\n")
            
            issues = result_item.get('issues', [])
            if issues:
                lines.append("**问题:**")
                for issue in issues:
                    lines.append(f"- {issue}")
                lines.append("")
            
            suggestions = result_item.get('suggestions', [])
            if suggestions:
                lines.append("**修改建议:**")
                for suggestion in suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")
            
            lines.append("---\n")
        
        return "\n".join(lines)
    
    def generate_word(self, result: Dict[str, Any]) -> bytes:
        doc = Document()
        
        title = doc.add_heading('标书对比分析报告', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"任务ID: {result['task_id']}")
        
        doc.add_heading('分析概览', level=1)
        doc.add_paragraph(f"需求数量: {result['requirements_count']}")
        doc.add_paragraph(f"问题数量: {result['issues_count']}")
        doc.add_paragraph(f"综合得分: {result['score']}分")
        
        doc.add_heading('详细分析', level=1)
        
        for idx, analysis in enumerate(result['analyses'], 1):
            req = analysis['requirement']
            result_item = analysis['analysis']
            
            doc.add_heading(f"{idx}. {req['category']}", level=2)
            doc.add_paragraph(f"要求: {req['requirement']}")
            doc.add_paragraph(f"位置: {req['location']}")
            doc.add_paragraph(f"是否强制: {'是' if req['is_mandatory'] else '否'}")
            
            status = result_item.get('status', '未知')
            severity = result_item.get('severity', '未知')
            
            doc.add_paragraph(f"状态: {status}")
            doc.add_paragraph(f"严重程度: {severity}")
            
            issues = result_item.get('issues', [])
            if issues:
                doc.add_paragraph("问题:", style='List Bullet')
                for issue in issues:
                    doc.add_paragraph(issue, style='List Bullet 2')
            
            suggestions = result_item.get('suggestions', [])
            if suggestions:
                doc.add_paragraph("修改建议:", style='List Bullet')
                for suggestion in suggestions:
                    doc.add_paragraph(suggestion, style='List Bullet 2')
            
            doc.add_paragraph()
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def save_report(self, result: Dict[str, Any], format: str, output_dir: str = "tasks") -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        task_id = result['task_id']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == "json":
            filename = f"{task_id}_{timestamp}.json"
            filepath = Path(output_dir) / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.generate_json(result))
        
        elif format == "markdown":
            filename = f"{task_id}_{timestamp}.md"
            filepath = Path(output_dir) / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.generate_markdown(result))
        
        elif format == "word":
            filename = f"{task_id}_{timestamp}.docx"
            filepath = Path(output_dir) / filename
            with open(filepath, 'wb') as f:
                f.write(self.generate_word(result))
        
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        return str(filepath)
