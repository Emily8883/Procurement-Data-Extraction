#!/usr/bin/env python3
"""
Deterministic Procurement Extraction Pipeline - Main Entry Point

Orchestrates the complete deterministic processing of procurement documents
with configurable rule-based routing, execution logging, and validation.

No manual decisions - everything deterministic and auditable.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from logging.execution_logger import PipelineLogger
from pipelines.document_router import DocumentTypeRouter
from pipelines.procurement_pipeline import ProcurementPipeline
from pipelines.specification_pipeline import SpecificationPipeline


class DeterministicPipeline:
    """Main deterministic pipeline orchestrator"""
    
    def __init__(self, config_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
        """Initialize pipeline with configuration"""
        if config_dir is None:
            config_dir = Path(__file__).parent / 'config'
        
        if log_dir is None:
            log_dir = Path(__file__).parent / 'logging' / 'logs'
        
        self.config_dir = Path(config_dir)
        self.log_dir = Path(log_dir)
        
        # Load configurations
        self.rules_config = self._load_config(self.config_dir / 'validation_rules.json')
        self.pipeline_config = self._load_config(self.config_dir / 'pipeline_config.json')
        
        # Initialize logger
        self.logger = PipelineLogger(self.log_dir)
        
        # Initialize router and pipelines
        self.router = DocumentTypeRouter(self.rules_config)
        self.procurement_pipeline = ProcurementPipeline(self.rules_config, self.pipeline_config, self.logger)
        self.specification_pipeline = SpecificationPipeline(self.rules_config, self.pipeline_config, self.logger)
        
        self.results = {
            'procurement': [],
            'specification': []
        }
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def process_documents(self, pdf_paths: List[str]) -> Dict[str, Any]:
        """
        Process multiple documents through deterministic pipeline
        
        Args:
            pdf_paths: List of PDF file paths
        
        Returns:
            Dictionary with results grouped by pipeline type
        """
        print(f"\n{'='*80}")
        print("DETERMINISTIC PROCUREMENT EXTRACTION PIPELINE")
        print(f"{'='*80}\n")
        print(f"Processing {len(pdf_paths)} document(s)\n")
        
        for pdf_path in pdf_paths:
            self.process_single_document(pdf_path)
        
        # Generate and save execution log
        execution_log_path = self.logger.save_execution_log()
        self.logger.print_session_summary()
        
        # Generate summary report
        summary = self._generate_summary()
        summary['execution_log_file'] = str(execution_log_path)
        
        return summary
    
    def process_single_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process single document through deterministic pipeline
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Processing result dictionary
        """
        pdf_path = Path(pdf_path)
        execution_id = self.logger.log_document_start(pdf_path.name)
        
        try:
            # Stage 1: Route document
            routing_decision, routing_confidence = self.router.route_document(str(pdf_path))
            
            # Select appropriate pipeline
            if routing_decision == 'procurement':
                pipeline = self.procurement_pipeline
            else:
                pipeline = self.specification_pipeline
            
            # Stage 2: Process document
            result = pipeline.process_document(str(pdf_path))
            
            # Stage 3: Log execution
            self.logger.log_execution(
                execution_id=execution_id,
                document_name=pdf_path.name,
                pipeline_used=result['pipeline_used'],
                document_type=result['pipeline_type'],
                extraction_confidence=result['extraction_confidence'],
                validation_result=result['validation_result'],
                validation_errors=result['validation_errors'],
                validation_warnings=result['validation_warnings'],
                processing_time_seconds=result['processing_time_seconds'],
                status=result['status'],
                failure_reason=result.get('failure_reason'),
                failure_details=result.get('failure_details'),
                routing_decision=routing_decision,
                routing_confidence=routing_confidence,
                extracted_fields=result.get('extracted_data'),
                metadata={
                    'routing_confidence': routing_confidence,
                    'enforcement_mode': pipeline.get_enforcement_mode()
                }
            )
            
            # Store results by pipeline type
            self.results[routing_decision].append(result)
            
            return result
            
        except Exception as e:
            # Log execution error
            self.logger.log_execution(
                execution_id=execution_id,
                document_name=pdf_path.name,
                pipeline_used='UNKNOWN',
                document_type='UNKNOWN',
                extraction_confidence=0,
                validation_result='FAIL',
                validation_errors=[str(e)],
                validation_warnings=[],
                processing_time_seconds=0,
                status='FAILED',
                failure_reason=f'Exception: {str(e)}',
                failure_details=str(e)
            )
            
            return {
                'document_name': pdf_path.name,
                'status': 'FAILED',
                'error': str(e)
            }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate processing summary"""
        return {
            'session_id': self.logger.session_id,
            'timestamp': datetime.now().isoformat(),
            'total_documents': len(self.logger.execution_logs),
            'by_pipeline': {
                'procurement': len(self.results['procurement']),
                'specification': len(self.results['specification'])
            },
            'results': self.results
        }
    
    def save_results(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Save results to output files
        
        Returns:
            Dictionary with output file paths
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / 'output'
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_files = {}
        
        # Save procurement results
        if self.results['procurement']:
            procurement_path = output_dir / f"deterministic_procurement_{timestamp}.json"
            with open(procurement_path, 'w', encoding='utf-8') as f:
                json.dump(self.results['procurement'], f, indent=2, ensure_ascii=False)
            output_files['procurement'] = procurement_path
            print(f"✅ Procurement results: {procurement_path}")
        
        # Save specification results
        if self.results['specification']:
            specification_path = output_dir / f"deterministic_specification_{timestamp}.json"
            with open(specification_path, 'w', encoding='utf-8') as f:
                json.dump(self.results['specification'], f, indent=2, ensure_ascii=False)
            output_files['specification'] = specification_path
            print(f"✅ Specification results: {specification_path}")
        
        # Save combined results
        if self.results['procurement'] or self.results['specification']:
            combined = {
                'session_id': self.logger.session_id,
                'timestamp': datetime.now().isoformat(),
                'procurement_documents': self.results['procurement'],
                'specification_documents': self.results['specification']
            }
            combined_path = output_dir / f"deterministic_pipeline_{timestamp}.json"
            with open(combined_path, 'w', encoding='utf-8') as f:
                json.dump(combined, f, indent=2, ensure_ascii=False)
            output_files['combined'] = combined_path
            print(f"✅ Combined results: {combined_path}")
        
        return output_files


def main():
    """Main execution"""
    # Initialize pipeline
    pipeline = DeterministicPipeline()
    
    # Example: Process PDFs from current directory
    pdf_dir = Path(__file__).parent / 'pdfs'
    if pdf_dir.exists():
        pdf_files = sorted(pdf_dir.glob('*.pdf'))
        
        if pdf_files:
            # Process all PDFs
            results = pipeline.process_documents([str(pdf) for pdf in pdf_files])
            
            # Save results
            output_files = pipeline.save_results()
            
            print(f"\n{'='*80}")
            print("PROCESSING COMPLETE")
            print(f"{'='*80}")
            print(f"\nResults Summary:")
            print(f"  Procurement documents: {results['by_pipeline']['procurement']}")
            print(f"  Specification documents: {results['by_pipeline']['specification']}")
            print(f"\nOutput files saved to: {Path(__file__).parent / 'output'}")
            print(f"Execution log: {Path(__file__).parent / 'logging' / 'logs'}")
            print(f"\n{'='*80}\n")
            
            return 0
        else:
            print(f"No PDF files found in {pdf_dir}")
            return 1
    else:
        print(f"PDF directory not found: {pdf_dir}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
