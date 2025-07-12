# app.py - Main Application File

import streamlit as st
import os
import json
import tempfile
from PIL import Image
import pandas as pd
from datetime import datetime

# Import the end-to-end processing functions
from end_to_end import (
    run_end_to_end_processing,
    run_step_1,
    run_step_2,
    run_step_3,
    run_step_4,
    run_step_5
)

# Page config
st.set_page_config(
    page_title="Question Card Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stAlert > div {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    /* Question text styling */
    .question-text {
        font-size: 16px !important;
        line-height: 1.6 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

def display_step_results(step_name, result, step_number):
    """Display results for each step with detailed information"""
    
    with st.expander(f"📊 {step_name} - Results", expanded=True):
        
        if result.get('success'):
            st.success(f"✅ {step_name} completed successfully!")
            
            # Display step-specific information
            if step_number == 1:  # Diagram Extraction
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Figures Extracted", result.get('total_figures', 0))
                with col2:
                    st.info(f"📁 Images saved to: {result.get('images_dir', 'N/A')}")
                
                # Display metadata if available
                if result.get('meta_path') and os.path.exists(result['meta_path']):
                    st.markdown("#### 🔍 Diagram Metadata")
                    with open(result['meta_path'], 'r') as f:
                        metadata = json.load(f)
                    st.json(metadata)
            
            elif step_number == 2:  # Diagram Mapping
                st.info(f"📄 Mapping file: {result.get('mapping_path', 'N/A')}")
                
                # Display mapping content if available
                if result.get('mapping_path') and os.path.exists(result['mapping_path']):
                    st.markdown("#### 🔍 Diagram Mapping Content")
                    with open(result['mapping_path'], 'r') as f:
                        mapping_data = json.load(f)
                    st.json(mapping_data)
            
            elif step_number == 3:  # Marks Extraction
                st.info(f"📄 Marks file: {result.get('marks_path', 'N/A')}")
                
                # Display marks content if available
                if result.get('marks_path') and os.path.exists(result['marks_path']):
                    st.markdown("#### 🔍 Marks Mapping Content")
                    with open(result['marks_path'], 'r') as f:
                        marks_data = json.load(f)
                    st.json(marks_data)
            
            elif step_number == 4:  # Full PDF Question Extraction
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📄 Questions file: {result.get('questions_path', 'N/A')}")
                with col2:
                    st.info(f"📄 Raw response file: {result.get('raw_response_path', 'N/A')}")
                
                # Display questions content if available
                if result.get('questions_path') and os.path.exists(result['questions_path']):
                    st.markdown("#### 🔍 Extracted Questions Preview")
                    with open(result['questions_path'], 'r', encoding='utf-8') as f:
                        questions_content = f.read()
                    
                    # Show first 2000 characters
                    preview_content = questions_content[:2000]
                    if len(questions_content) > 2000:
                        preview_content += "\n\n... (truncated for display)"
                    
                    st.text_area("Questions Content", preview_content, height=300)
                    
                    # Provide download button
                    st.download_button(
                        label="📥 Download Full Questions File",
                        data=questions_content,
                        file_name=f"extracted_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown"
                    )
            
            elif step_number == 5:  # Question Card Generation
                if result.get('cards_generated'):
                    st.success("🎴 Question cards have been generated and are displayed below!")
                    st.info(f"📄 PDF processed: {result.get('pdf_filename', 'N/A')}")
                    st.info("💡 **Note:** The question cards are rendered below this summary table. Scroll down to see them!")
                else:
                    st.warning("🎴 Question cards were not generated")
        
        else:
            st.error(f"❌ {step_name} failed!")
            st.error(f"Error: {result.get('error', 'Unknown error')}")

def main():
    """Main Streamlit app"""
    
    # Title and description
    st.title("📚 Question Card Generator")
    st.markdown("**Upload a PDF to extract questions, diagrams, and marks mapping**")
    
    # Sidebar for configuration
    st.sidebar.header("⚙️ Configuration")
    
    # Processing mode selection
    processing_mode = st.sidebar.selectbox(
        "Processing Mode",
        ["End-to-End Processing", "Individual Steps"],
        help="Choose whether to run all steps together or test individual steps"
    )
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload a CBSE Mathematics question paper PDF"
    )
    
    if uploaded_file is not None:
        st.success(f"📄 File uploaded: {uploaded_file.name}")
        
        # Display file info
        file_size = len(uploaded_file.getvalue())
        st.info(f"📊 File size: {file_size / 1024:.2f} KB")
        
        # Processing buttons
        if processing_mode == "End-to-End Processing":
            st.markdown("---")
            st.subheader("🚀 End-to-End Processing")
            
            if st.button("▶️ Run Complete Pipeline", type="primary"):
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Results container
                results_container = st.container()
                
                # Callback to update progress
                def progress_callback(message, status):
                    status_text.text(message)
                    
                    # Update progress bar based on step
                    if "Step 1" in message:
                        progress_bar.progress(0.20)
                    elif "Step 2" in message:
                        progress_bar.progress(0.40)
                    elif "Step 3" in message:
                        progress_bar.progress(0.60)
                    elif "Step 4" in message:
                        progress_bar.progress(0.80)
                    elif "Step 5" in message:
                        progress_bar.progress(1.0)
                
                # Run processing
                with st.spinner("Processing..."):
                    results = run_end_to_end_processing(uploaded_file, step_callback=progress_callback)
                
                # Display results
                with results_container:
                    st.markdown("---")
                    st.subheader("📊 Processing Results")
                    
                    if results['success']:
                        st.success("🎉 Processing completed successfully!")
                        
                        # Display final outputs summary
                        st.markdown("### 📋 Final Outputs Summary")
                        
                        summary_data = {
                            "Output Type": [],
                            "Value": [],
                            "Status": []
                        }
                        
                        for key, value in results['final_outputs'].items():
                            summary_data["Output Type"].append(key.replace('_', ' ').title())
                            summary_data["Value"].append(str(value) if value else "Not available")
                            summary_data["Status"].append("✅ Available" if value else "❌ Not available")
                        
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True)
                        
                        # Display step-by-step results
                        st.markdown("### 🔍 Step-by-Step Results")
                        
                        for step_key, step_result in results['step_results'].items():
                            step_number = int(step_key.replace('step', ''))
                            step_names = {
                                1: "Diagram Extraction",
                                2: "Diagram Mapping", 
                                3: "Marks Extraction",
                                4: "Full PDF Question Extraction",
                                5: "Question Card Generation"
                            }
                            display_step_results(step_names.get(step_number, f"Step {step_number}"), 
                                               step_result, step_number)
                    
                    else:
                        st.error("❌ Processing failed!")
                        
                        if results['errors']:
                            st.markdown("### 🚨 Errors")
                            for error in results['errors']:
                                st.error(f"• {error}")
        
        else:  # Individual Steps
            st.markdown("---")
            st.subheader("🔧 Individual Step Testing")
            
            # Create columns for step buttons
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("1️⃣ Diagram Extraction"):
                    with st.spinner("Extracting diagrams..."):
                        result = run_step_1(uploaded_file)
                    display_step_results("Diagram Extraction", result, 1)
            
            with col2:
                if st.button("2️⃣ Diagram Mapping"):
                    with st.spinner("Mapping diagrams..."):
                        result = run_step_2(uploaded_file)
                    display_step_results("Diagram Mapping", result, 2)
            
            with col3:
                if st.button("3️⃣ Marks Extraction"):
                    with st.spinner("Extracting marks..."):
                        result = run_step_3(uploaded_file)
                    display_step_results("Marks Extraction", result, 3)
            
            with col4:
                if st.button("4️⃣ Question Extraction"):
                    with st.spinner("Extracting questions..."):
                        result = run_step_4(uploaded_file)
                    display_step_results("Full PDF Question Extraction", result, 4)
            
            with col5:
                if st.button("5️⃣ Question Cards"):
                    with st.spinner("Generating question cards..."):
                        result = run_step_5(uploaded_file)
                    display_step_results("Question Card Generation", result, 5)
    
    else:
        st.info("👆 Please upload a PDF file to begin processing")
    
    # Footer
    st.markdown("---")
    st.markdown("**Note:** This tool is designed for CBSE Mathematics question papers. Make sure your PDF is clear and readable for best results.")

if __name__ == "__main__":
    main()
