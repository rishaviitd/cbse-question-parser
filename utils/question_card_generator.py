import streamlit as st
import os
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import base64
import io
from .data_integrator import ParsedQuestion, DiagramInfo, DataIntegrator

class QuestionCardGenerator:
    """Generates beautiful UI cards for questions"""
    
    def __init__(self):
        self.question_type_colors = {
            'MCQ': '#e3f2fd',  # Light blue
            'Case Study': '#f3e5f5',  # Light purple
            'Normal Subjective': '#e8f5e8',  # Light green
            'Internal Choice Subjective': '#fff3e0',  # Light orange
            'Assertion Reasoning': '#fce4ec',  # Light pink
            'Unknown': '#f5f5f5'  # Light gray
        }
        
        self.question_type_icons = {
            'MCQ': '🔘',
            'Case Study': '📚',
            'Normal Subjective': '✍️',
            'Internal Choice Subjective': '🔀',
            'Assertion Reasoning': '🤔',
            'Unknown': '❓'
        }
    
    def generate_cards(self, questions: List[ParsedQuestion]) -> None:
        """Generate and display cards for all questions"""
        if not questions:
            st.warning("No questions found to display.")
            return
        
        st.header(f"📋 Question Cards ({len(questions)} questions)")
        
        # Add filters
        self._add_filters(questions)
        
        # Get filtered questions
        filtered_questions = self._apply_filters(questions)
        
        if not filtered_questions:
            st.warning("No questions match the selected filters.")
            return
        
        # Display cards
        for i, question in enumerate(filtered_questions):
            self._render_question_card(question, i + 1)
    
    def _add_filters(self, questions: List[ParsedQuestion]) -> None:
        """Add filter controls"""
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Question type filter
                question_types = list(set(q.question_type for q in questions))
                selected_types = st.multiselect(
                    "Question Types",
                    options=question_types,
                    default=question_types,
                    key="question_type_filter"
                )
            
            with col2:
                # Has diagrams filter
                has_diagrams_options = ["All", "With Diagrams", "Without Diagrams"]
                diagrams_filter = st.selectbox(
                    "Diagrams",
                    options=has_diagrams_options,
                    key="diagrams_filter"
                )
            
            with col3:
                # Internal choice filter
                choice_options = ["All", "With Internal Choice", "Without Internal Choice"]
                choice_filter = st.selectbox(
                    "Internal Choice",
                    options=choice_options,
                    key="choice_filter"
                )
    
    def _apply_filters(self, questions: List[ParsedQuestion]) -> List[ParsedQuestion]:
        """Apply filters to questions"""
        filtered = questions
        
        # Apply question type filter
        if 'question_type_filter' in st.session_state:
            selected_types = st.session_state.question_type_filter
            if selected_types:
                filtered = [q for q in filtered if q.question_type in selected_types]
        
        # Apply diagrams filter
        if 'diagrams_filter' in st.session_state:
            diagrams_filter = st.session_state.diagrams_filter
            if diagrams_filter == "With Diagrams":
                filtered = [q for q in filtered if q.diagrams]
            elif diagrams_filter == "Without Diagrams":
                filtered = [q for q in filtered if not q.diagrams]
        
        # Apply internal choice filter
        if 'choice_filter' in st.session_state:
            choice_filter = st.session_state.choice_filter
            if choice_filter == "With Internal Choice":
                filtered = [q for q in filtered if q.has_internal_choice]
            elif choice_filter == "Without Internal Choice":
                filtered = [q for q in filtered if not q.has_internal_choice]
        
        return filtered
    
    def _parse_question_and_options(self, text: str) -> Tuple[str, List[str]]:
        """
        Parse question text to separate main question from options
        Returns: (main_question, list_of_options)
        """
        import re
        
        # Handle internal choice markers
        text = text.replace('[%OR%]', '\n\n**OR**\n\n')
        text = text.replace('[%or%]', '\n\n**or**\n\n')
        
        lines = text.split('\n')
        main_question_lines = []
        options = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Check if line is an option (starts with (a), (b), (c), (d), etc.)
                option_match = re.match(r'^\([a-d]\)\s*(.+)', line)
                if option_match:
                    options.append(line)
                else:
                    main_question_lines.append(line)
        
        main_question = '\n'.join(main_question_lines)
        return main_question, options
    
    def _render_question_card(self, question: ParsedQuestion, card_number: int) -> None:
        """Render a single question card"""
        # Card container with custom styling
        card_color = self.question_type_colors.get(question.question_type, '#f5f5f5')
        icon = self.question_type_icons.get(question.question_type, '❓')
        
        with st.container():
            # Card header
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"""
                <div style="background-color: {card_color}; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                    <h3 style="margin: 0; color: #1f77b4;">
                        {icon} Question {question.question_number}
                    </h3>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background-color: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <strong>Type:</strong><br>{question.question_type}
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                marks_display = self._format_marks(question.marks)
                st.markdown(f"""
                <div style="background-color: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <strong>Marks:</strong><br>{marks_display}
                </div>
                """, unsafe_allow_html=True)
            
            # Question content using native Streamlit markdown for proper LaTeX
            st.markdown("**Question Text:**")
            
            # Parse question and options
            main_question, options = self._parse_question_and_options(question.question_text)
            
            # Display main question using native markdown (LaTeX will render properly)
            with st.container():
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; margin: 10px 0;">
                """, unsafe_allow_html=True)
                
                # Use native markdown for LaTeX rendering
                st.markdown(main_question)
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Display options vertically if they exist
            if options:
                st.markdown("**Options:**")
                st.markdown("")  # Add some spacing
                
                for option in options:
                    # Display each option cleanly without bullet points
                    st.markdown(option)
                
                st.markdown("")  # Add spacing after options
            
            # Internal choice handling
            if question.has_internal_choice:
                self._render_internal_choice_native(question)
            
            # Diagrams section
            if question.diagrams:
                self._render_diagrams(question.diagrams)
            
            # Card footer with additional info
            with st.expander(f"📊 Additional Info - Question {question.question_number}"):
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.write("**Question Details:**")
                    st.write(f"- Question Number: {question.question_number}")
                    st.write(f"- Question Type: {question.question_type}")
                    st.write(f"- Has Internal Choice: {'Yes' if question.has_internal_choice else 'No'}")
                    st.write(f"- Number of Diagrams: {len(question.diagrams)}")
                
                with info_col2:
                    st.write("**Marks Information:**")
                    if isinstance(question.marks, list):
                        for i, mark in enumerate(question.marks):
                            st.write(f"- Choice {i+1}: {mark}")
                    else:
                        st.write(f"- Marks: {question.marks}")
            
            # Separator
            st.markdown("---")
    
    def _format_marks(self, marks: Any) -> str:
        """Format marks for display"""
        if isinstance(marks, list):
            return f"{len(marks)} choices"
        elif isinstance(marks, str):
            return marks
        elif isinstance(marks, (int, float)):
            return f"{marks} marks"
        else:
            return str(marks)
    
    def _render_internal_choice_native(self, question: ParsedQuestion) -> None:
        """Render internal choice options using Streamlit's native markdown"""
        st.markdown("### 🔀 Internal Choice Options:")
        
        if question.choice_parts:
            for i, part in enumerate(question.choice_parts):
                st.markdown(f"""
                <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; border-left: 4px solid #f57c00; margin: 10px 0;">
                    <strong style="font-size: 16px; color: #f57c00;">Choice {i+1}:</strong>
                </div>
                """, unsafe_allow_html=True)
                
                # Parse this choice part for question and options
                main_question, options = self._parse_question_and_options(part)
                
                # Display the choice content using native markdown
                st.markdown(main_question)
                
                # Display options for this choice if any
                if options:
                    for option in options:
                        st.markdown(f"- {option}")
                
                if i < len(question.choice_parts) - 1:
                    st.markdown("---")
    
    def _render_diagrams(self, diagrams: List[DiagramInfo]) -> None:
        """Render diagrams section"""
        st.markdown("""
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4 style="color: #1976d2; margin-top: 0;">📊 Associated Diagrams:</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Display diagrams in columns
        if len(diagrams) == 1:
            self._render_single_diagram(diagrams[0])
        else:
            # Multiple diagrams in columns
            cols = st.columns(min(len(diagrams), 3))
            for i, diagram in enumerate(diagrams):
                with cols[i % 3]:
                    self._render_single_diagram(diagram)
    
    def _render_single_diagram(self, diagram: DiagramInfo) -> None:
        """Render a single diagram"""
        try:
            if os.path.exists(diagram.image_path):
                image = Image.open(diagram.image_path)
                
                # Create diagram info
                choice_info = ""
                if diagram.choice_location and diagram.choice_location != "null":
                    choice_info = f" (Choice: {diagram.choice_location})"
                
                st.markdown(f"""
                <div style="background-color: white; padding: 10px; border-radius: 5px; margin: 5px 0; text-align: center;">
                    <strong>{diagram.figure_id}</strong> - Page {diagram.page_number}{choice_info}
                </div>
                """, unsafe_allow_html=True)
                
                st.image(image, caption=f"{diagram.figure_id}", use_column_width=True)
            else:
                st.warning(f"Image not found: {diagram.image_path}")
        except Exception as e:
            st.error(f"Error loading diagram {diagram.figure_id}: {str(e)}")
    
    def export_cards_summary(self, questions: List[ParsedQuestion]) -> Dict[str, Any]:
        """Export a summary of all cards"""
        summary = {
            'total_questions': len(questions),
            'question_types': {},
            'questions_with_diagrams': 0,
            'questions_with_internal_choice': 0,
            'total_diagrams': 0
        }
        
        for question in questions:
            # Count question types
            q_type = question.question_type
            summary['question_types'][q_type] = summary['question_types'].get(q_type, 0) + 1
            
            # Count diagrams
            if question.diagrams:
                summary['questions_with_diagrams'] += 1
                summary['total_diagrams'] += len(question.diagrams)
            
            # Count internal choices
            if question.has_internal_choice:
                summary['questions_with_internal_choice'] += 1
        
        return summary

def generate_question_cards(pdf_filename: str) -> None:
    """Main function to generate question cards for a PDF"""
    st.markdown("### 🔧 Data Integration Process")
    with st.spinner("Loading and integrating data from all pipeline steps..."):
        # Initialize data integrator
        integrator = DataIntegrator()
        
        # Load pipeline outputs
        if not integrator.load_pipeline_outputs(pdf_filename):
            st.error("Failed to load pipeline outputs. Please ensure all pipeline steps have been completed.")
            return
    
        # Display data summary
        summary = integrator.get_summary()
        st.info(f"""
        **Data Summary:**
        - Diagrams loaded: {summary['diagrams_loaded']}
        - Diagram mappings: {summary['diagram_mappings_loaded']}
        - Marks mappings: {summary['marks_mappings_loaded']}
        - Full questions loaded: {summary['full_questions_loaded']}
        - Questions extracted: {summary['questions_extracted']}
        - Page-wise questions: {summary['page_wise_questions_loaded']}
        """)
    
    # Parse questions
    with st.spinner("Parsing questions and integrating with diagrams and marks..."):
        questions = integrator.parse_questions()
    
    if not questions:
        st.warning("No questions could be parsed from the data.")
        st.info("💡 **Debug Info:** Check if the full questions file contains properly formatted questions with [####] separators.")
        return
    
    # Generate cards
    card_generator = QuestionCardGenerator()
    card_generator.generate_cards(questions)
    
    # Export summary
    cards_summary = card_generator.export_cards_summary(questions)
    
    with st.expander("📈 Cards Summary"):
        st.json(cards_summary) 