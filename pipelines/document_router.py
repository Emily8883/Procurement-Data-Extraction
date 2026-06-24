#!/usr/bin/env python3
"""
Document Type Router - Deterministic Classification

Routes documents to appropriate pipeline (procurement or specification)
based on configurable, rule-based classification with no manual options.
"""

import json
import re
from typing import Dict, Any, Tuple, List
from pathlib import Path


class DocumentTypeRouter:
    """Deterministic document router"""
    
    def __init__(self, rules_config: Dict[str, Any]):
        """Initialize router with routing rules"""
        self.rules = rules_config.get('routing_rules', {})
        self.procurement_keywords = set(self.rules.get('classification_keywords', {}).get('procurement', []))
        self.specification_keywords = set(self.rules.get('classification_keywords', {}).get('specification', []))
    
    def route_document(self, pdf_path: str, extraction_result: Dict[str, Any] = None) -> Tuple[str, float]:
        """
        Route document to appropriate pipeline
        
        Returns:
            (pipeline_type, confidence_score)
            pipeline_type: 'procurement' or 'specification'
            confidence_score: 0.0 to 1.0
        """
        pdf_path = Path(pdf_path)
        
        # Stage 1: Extract text from PDF to analyze
        document_text = self._extract_text_for_analysis(str(pdf_path))
        
        # Stage 2: Analyze document
        procurement_score = self._score_procurement(document_text, extraction_result)
        specification_score = self._score_specification(document_text, extraction_result)
        
        # Stage 3: Make deterministic decision
        if procurement_score > specification_score:
            return 'procurement', procurement_score
        elif specification_score > procurement_score:
            return 'specification', specification_score
        else:
            # Tie - use fallback logic
            return self._apply_fallback_logic(document_text, extraction_result)
    
    def _extract_text_for_analysis(self, pdf_path: str) -> str:
        """Extract text from PDF for analysis"""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages[:3]:  # First 3 pages
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + " "
                return text.lower()
        except Exception as e:
            return ""
    
    def _score_procurement(self, text: str, extraction: Dict = None) -> float:
        """Score likelihood of procurement document"""
        score = 0.0
        max_score = 10.0
        
        # Keyword matching
        matches = sum(1 for kw in self.procurement_keywords if kw in text)
        score += min(matches / 2, 3.0)  # Max 3 points for keywords
        
        # Extraction-based signals
        if extraction:
            # Has supplier
            if extraction.get('supplier') and extraction['supplier'] != "":
                score += 2.0
            
            # Has invoice/PO number
            if extraction.get('invoice_or_po_number') and extraction['invoice_or_po_number'] != "":
                score += 2.0
            
            # Has pricing
            if (extraction.get('subtotal') and extraction['subtotal'] != "") or \
               (extraction.get('total_amount') and extraction['total_amount'] != ""):
                score += 2.0
            
            # Has issue date
            if extraction.get('issue_date') and extraction['issue_date'] != "":
                score += 1.0
        
        # Text patterns
        if re.search(r'total|subtotal|tax|cantidad|precio', text):
            score += 1.0
        
        return min(score / max_score, 1.0)
    
    def _score_specification(self, text: str, extraction: Dict = None) -> float:
        """Score likelihood of specification document"""
        score = 0.0
        max_score = 10.0
        
        # Keyword matching
        matches = sum(1 for kw in self.specification_keywords if kw in text)
        score += min(matches / 2, 3.0)  # Max 3 points for keywords
        
        # Extraction-based signals
        if extraction:
            # Missing supplier
            if not extraction.get('supplier') or extraction['supplier'] == "":
                score += 1.5
            
            # Missing pricing
            if (not extraction.get('subtotal') or extraction['subtotal'] == "") and \
               (not extraction.get('total_amount') or extraction['total_amount'] == ""):
                score += 2.0
            
            # Missing issue date
            if not extraction.get('issue_date') or extraction['issue_date'] == "":
                score += 1.5
            
            # Has line items with technical content
            if extraction.get('line_items'):
                line_text = " ".join([str(item.get('description', '')) for item in extraction['line_items']])
                if re.search(r'standard|norm|requirement|specification|feature|technical|temperature|voltage', 
                           line_text.lower()):
                    score += 2.0
        
        # Text patterns
        if re.search(r'specification|requirement|standard|norm|datasheet|technical|feature|characteristic', text):
            score += 1.0
        
        if re.search(r'material|dimension|weight|temperature|voltage|current', text):
            score += 1.0
        
        return min(score / max_score, 1.0)
    
    def _apply_fallback_logic(self, text: str, extraction: Dict = None) -> Tuple[str, float]:
        """Apply fallback routing logic when scores are tied"""
        fallback = self.rules.get('fallback_logic', {})
        
        # Check override rules
        override_rules = self.rules.get('override_rules', {})
        
        # Rule 1: Explicit supplier presence
        if extraction and extraction.get('supplier') and extraction['supplier'] != "":
            return 'procurement', 0.6
        
        # Rule 2: Explicit pricing presence
        if extraction and (
            (extraction.get('total_amount') and extraction['total_amount'] != "") or
            (extraction.get('subtotal') and extraction['subtotal'] != "")
        ):
            return 'procurement', 0.6
        
        # Rule 3: Explicit technical requirements
        if extraction and extraction.get('line_items'):
            line_text = " ".join([
                str(item.get('description', '')).lower() 
                for item in extraction['line_items']
            ])
            if any(kw in line_text for kw in 
                   ['specification', 'requirement', 'standard', 'norm', 'feature']):
                return 'specification', 0.6
        
        # Rule 4: No pricing data
        if extraction and (
            (not extraction.get('total_amount') or extraction['total_amount'] == "") and
            (not extraction.get('subtotal') or extraction['subtotal'] == "")
        ):
            return 'specification', 0.6
        
        # Default fallback
        default_route = fallback.get('default_route', 'procurement')
        return default_route, 0.5
    
    def is_confident_routing(self, confidence: float, threshold: float = 0.6) -> bool:
        """Check if routing confidence exceeds threshold"""
        return confidence >= threshold
    
    def get_routing_explanation(self, pdf_path: str, pipeline_type: str, confidence: float) -> str:
        """Generate human-readable explanation for routing decision"""
        explanation = f"Document '{Path(pdf_path).name}' routed to {pipeline_type.upper()} "
        explanation += f"pipeline (confidence: {confidence*100:.0f}%)\n"
        
        if pipeline_type == 'procurement':
            explanation += "Reason: Document contains procurement-related content "
            explanation += "(invoice, PO, supplier, pricing information)"
        else:
            explanation += "Reason: Document contains specification content "
            explanation += "(technical requirements, standards, no pricing)"
        
        return explanation
