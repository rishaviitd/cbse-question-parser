import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from PIL import Image

@dataclass
class DiagramInfo:
    """Information about a diagram/figure"""
    figure_id: str
    page_number: int
    image_path: str
    question_identifier: Optional[str] = None
    choice_location: Optional[str] = None  # "first", "second", "null"

@dataclass
class QuestionMarks:
    """Marks information for a question"""
    question_type: str
    marks: Any  # Can be int, str, or list depending on question type

@dataclass
class ParsedQuestion:
    """A parsed question with all associated data"""
    question_number: str
    question_text: str
    question_type: str
    marks: Any
    diagrams: List[DiagramInfo] = field(default_factory=list)
    has_internal_choice: bool = False
    choice_parts: List[str] = field(default_factory=list)  # For internal choice questions

class DataIntegrator:
    """Integrates data from all pipeline steps"""
    
    def __init__(self, base_logs_dir: str = "logs"):
        self.base_logs_dir = base_logs_dir
        self.diagrams_data = {}
        self.diagram_mappings = {}
        self.marks_mappings = {}
        self.full_questions_text = ""
        self.page_wise_questions = []
        
    def load_pipeline_outputs(self, pdf_filename: str) -> bool:
        """
        Load all pipeline outputs for a given PDF file
        
        Args:
            pdf_filename: Name of the PDF file (without extension)
            
        Returns:
            bool: True if all required data was loaded successfully
        """
        try:
            # Load diagram data
            self._load_diagram_data()
            
            # Load diagram mappings
            self._load_diagram_mappings(pdf_filename)
            
            # Load marks mappings
            self._load_marks_mappings(pdf_filename)
            
            # Load full PDF questions
            self._load_full_questions(pdf_filename)
            
            # Load page-wise questions (optional)
            self._load_page_wise_questions(pdf_filename)
            
            return True
            
        except Exception as e:
            print(f"Error loading pipeline outputs: {str(e)}")
            return False
    
    def _load_diagram_data(self):
        """Load diagram metadata and images"""
        diagrams_dir = os.path.join(self.base_logs_dir, "diagrams")
        meta_path = os.path.join(diagrams_dir, "meta_data.json")
        
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                self.diagrams_data = json.load(f)
    
    def _load_diagram_mappings(self, pdf_filename: str):
        """Load diagram to question mappings"""
        mappings_dir = os.path.join(self.base_logs_dir, "diagram_mappings")
        
        # Look for mapping files that match the PDF filename or get the most recent file
        if os.path.exists(mappings_dir):
            json_files = [f for f in os.listdir(mappings_dir) if f.endswith('.json')]
            
            if json_files:
                # First try to find exact match
                for filename in json_files:
                    if filename.startswith(pdf_filename):
                        mapping_path = os.path.join(mappings_dir, filename)
                        with open(mapping_path, 'r') as f:
                            self.diagram_mappings = json.load(f)
                        return
                
                # If no exact match, take the most recent file
                json_files.sort(key=lambda x: os.path.getmtime(os.path.join(mappings_dir, x)), reverse=True)
                mapping_path = os.path.join(mappings_dir, json_files[0])
                with open(mapping_path, 'r') as f:
                    self.diagram_mappings = json.load(f)
                print(f"Used most recent diagram mapping file: {json_files[0]}")
    
    def _load_marks_mappings(self, pdf_filename: str):
        """Load marks and question type mappings"""
        marks_dir = os.path.join(self.base_logs_dir, "marks_mappings")
        marks_path = os.path.join(marks_dir, f"{pdf_filename}.json")
        
        # First try exact filename match
        if os.path.exists(marks_path):
            with open(marks_path, 'r') as f:
                self.marks_mappings = json.load(f)
            return
        
        # If no exact match, get the most recent file
        if os.path.exists(marks_dir):
            json_files = [f for f in os.listdir(marks_dir) if f.endswith('.json')]
            if json_files:
                json_files.sort(key=lambda x: os.path.getmtime(os.path.join(marks_dir, x)), reverse=True)
                marks_path = os.path.join(marks_dir, json_files[0])
                with open(marks_path, 'r') as f:
                    self.marks_mappings = json.load(f)
                print(f"Used most recent marks mapping file: {json_files[0]}")
    
    def _load_full_questions(self, pdf_filename: str):
        """Load full PDF questions text"""
        questions_dir = os.path.join(self.base_logs_dir, "full_pdf_questions")
        questions_path = os.path.join(questions_dir, f"{pdf_filename}.md")
        
        # First try exact filename match
        if os.path.exists(questions_path):
            with open(questions_path, 'r', encoding='utf-8') as f:
                self.full_questions_text = f.read()
            return
        
        # If no exact match, get the most recent file
        if os.path.exists(questions_dir):
            md_files = [f for f in os.listdir(questions_dir) if f.endswith('.md')]
            if md_files:
                md_files.sort(key=lambda x: os.path.getmtime(os.path.join(questions_dir, x)), reverse=True)
                questions_path = os.path.join(questions_dir, md_files[0])
                with open(questions_path, 'r', encoding='utf-8') as f:
                    self.full_questions_text = f.read()
                print(f"Used most recent questions file: {md_files[0]}")
    
    def _load_page_wise_questions(self, pdf_filename: str):
        """Load page-wise questions (optional)"""
        gemini_dir = os.path.join(self.base_logs_dir, "gemini_questions")
        
        if os.path.exists(gemini_dir):
            page_files = [f for f in os.listdir(gemini_dir) if f.startswith("page_") and f.endswith(".md")]
            page_files.sort()  # Sort to maintain order
            
            for page_file in page_files:
                page_path = os.path.join(gemini_dir, page_file)
                with open(page_path, 'r', encoding='utf-8') as f:
                    self.page_wise_questions.append(f.read())
    
    def parse_questions(self) -> List[ParsedQuestion]:
        """
        Parse questions from the full questions text and integrate with other data
        
        Returns:
            List[ParsedQuestion]: List of parsed questions with integrated data
        """
        if not self.full_questions_text:
            return []
        
        # Split questions using [####] separator
        question_blocks = self.full_questions_text.split('[####]')
        question_blocks = [block.strip() for block in question_blocks if block.strip()]
        
        parsed_questions = []
        
        for block in question_blocks:
            question = self._parse_single_question(block)
            if question:
                parsed_questions.append(question)
        
        return parsed_questions
    
    def _parse_single_question(self, question_block: str) -> Optional[ParsedQuestion]:
        """Parse a single question block"""
        if not question_block.strip():
            return None
        
        # Extract question number (first line usually contains it)
        lines = question_block.split('\n')
        first_line = lines[0].strip()
        
        # Extract question number using regex
        question_number = self._extract_question_number(first_line)
        if not question_number:
            return None
        
        # Check if question has internal choice
        has_internal_choice = '[%OR%]' in question_block
        choice_parts = []
        
        if has_internal_choice:
            # Split by [%OR%] to get choice parts
            parts = question_block.split('[%OR%]')
            choice_parts = [part.strip() for part in parts]
        
        # Get question type and marks from mappings
        question_key = f"question-{question_number}"
        marks_info = self.marks_mappings.get(question_key, {})
        question_type = marks_info.get('question_type', 'Unknown')
        marks = marks_info.get('marks', 0)
        
        # Get associated diagrams
        diagrams = self._get_question_diagrams(question_number)
        
        return ParsedQuestion(
            question_number=question_number,
            question_text=question_block,
            question_type=question_type,
            marks=marks,
            diagrams=diagrams,
            has_internal_choice=has_internal_choice,
            choice_parts=choice_parts
        )
    
    def _extract_question_number(self, text: str) -> Optional[str]:
        """Extract question number from text"""
        # Look for patterns like "1.", "2.", "Q1", "Question 1", etc.
        patterns = [
            r'^(\d+)\.',  # "1.", "2.", etc.
            r'^Q(\d+)',   # "Q1", "Q2", etc.
            r'^Question\s+(\d+)',  # "Question 1", etc.
            r'^(\d+)\s',  # "1 ", "2 ", etc.
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _get_question_diagrams(self, question_number: str) -> List[DiagramInfo]:
        """Get diagrams associated with a question"""
        diagrams = []
        
        # Look through diagram mappings
        for figure_key, mapping in self.diagram_mappings.items():
            if mapping.get('question_identifier') == question_number:
                # Find the figure in diagrams_data
                figure_info = self._find_figure_info(figure_key)
                if figure_info:
                    diagram = DiagramInfo(
                        figure_id=figure_key,
                        page_number=figure_info.get('page', 1),
                        image_path=figure_info.get('path', ''),
                        question_identifier=question_number,
                        choice_location=mapping.get('choice_location', 'null')
                    )
                    diagrams.append(diagram)
        
        return diagrams
    
    def _find_figure_info(self, figure_key: str) -> Optional[Dict]:
        """Find figure information in diagrams data"""
        if 'figures' in self.diagrams_data:
            for figure in self.diagrams_data['figures']:
                if f"figure-{figure.get('figure_id')}" == figure_key:
                    return figure
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded data"""
        return {
            'diagrams_loaded': len(self.diagrams_data.get('figures', [])),
            'diagram_mappings_loaded': len(self.diagram_mappings),
            'marks_mappings_loaded': len(self.marks_mappings),
            'full_questions_loaded': bool(self.full_questions_text),
            'page_wise_questions_loaded': len(self.page_wise_questions),
            'questions_extracted': len(self.full_questions_text.split('[####]')) - 1 if self.full_questions_text else 0
        } 