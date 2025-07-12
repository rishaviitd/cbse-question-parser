import os
import streamlit as st
from utils import process_pdf, extract_questions_from_folder
from logs.logger import init_job_logging, log_diagram_snippets, log_gemini_response
import tempfile
from api.gemini import generate_markdown_from_pdf
from api.full_pdf_question_extraction import extract_questions_from_pdf
from logic.diagram_extraction import extract_diagrams_from_pdf
from pdf2image import convert_from_bytes
import io, base64
import cv2
from PIL import Image
import json
from api.gemini_diagram_mapping import generate_diagram_mapping
from api.gemini_marks_mapping import generate_marks_mapping
from utils.question_card_generator import generate_question_cards
from end_to_end import run_step_1, run_step_2, run_step_3, run_step_4, run_step_5, run_end_to_end_processing

def process_pdf_and_generate_cards(uploaded_file):
    """Process PDF through the complete pipeline and generate question cards"""
    try:
        # Step callback for progress updates
        def step_callback(message, status):
            if status == "success":
                st.success(message)
            elif status == "error":
                st.error(message)
            elif status == "warning":
                st.warning(message)
            else:
                st.info(message)
        
        # Run the complete end-to-end processing
        results = run_end_to_end_processing(uploaded_file, step_callback)
        
        if results['success']:
            st.success("🎉 PDF processing completed successfully!")
            
            # Extract filename for card generation
            pdf_filename = os.path.splitext(uploaded_file.name)[0]
            
            # Generate question cards
            st.info("🎴 Generating question cards...")
            generate_question_cards(pdf_filename)
            st.success("✅ Question cards generated successfully!")
            
        else:
            st.error("❌ PDF processing failed!")
            if results['errors']:
                st.error("**Errors encountered:**")
                for error in results['errors']:
                    st.error(f"• {error}")
            
    except Exception as e:
        st.error(f"Fatal error during processing: {str(e)}")
        st.info("Please check the PDF format and try again.")

def pdf_to_image(pdf_bytes):
    """
    Convert PDF to an image for display
    
    Args:
        pdf_bytes (bytes): PDF file content
    
    Returns:
        PIL.Image: First page of the PDF as an image
    """
    try:
        # Convert PDF to image
        pages = convert_from_bytes(pdf_bytes)
        return pages[0] if pages else None
    except Exception as e:
        st.error(f"Error converting PDF to image: {e}")
        return None

def run_app():
    tabs = st.tabs(["Extract Diagrams", "Map Diagrams", "PDF Splitting", "Extract Questions", "Full PDF Question Extraction", "Extract Marks", "End-to-End", "Question Cards"])

    # Extract Diagrams Tab
    with tabs[0]:
        st.header("Extract Diagrams")
        uploaded_diagram_file = st.file_uploader(
            "Upload PDF for Diagram Extraction", type=["pdf"], key="diagram_pdf"
        )
        if uploaded_diagram_file is not None:
            file_key3 = f"{uploaded_diagram_file.name}_{uploaded_diagram_file.size}"
            if "diagram_file_paths" not in st.session_state:
                st.session_state.diagram_file_paths = {}
            if file_key3 not in st.session_state.diagram_file_paths:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_diag:
                    tmp_diag.write(uploaded_diagram_file.read())
                    st.session_state.diagram_file_paths[file_key3] = tmp_diag.name
            temp_diag_path = st.session_state.diagram_file_paths[file_key3]
            st.write(f"File saved for extraction: `{temp_diag_path}`")
            conf = st.slider(
                "Confidence Threshold", 0.0, 1.0, 0.25, 0.05, key="diag_conf"
            )
            iou = st.slider(
                "IOU Threshold", 0.0, 1.0, 0.45, 0.05, key="diag_iou"
            )
            if st.button("Extract Diagrams", key="extract_diagrams_button"):
                with st.spinner("Extracting diagrams..."):
                    parsed_images, figure_snippets = extract_diagrams_from_pdf(temp_diag_path, conf, iou)
                st.success("Extraction successful!")
                # Log and save figure snippets
                images_dir, meta_path = log_diagram_snippets(figure_snippets)
                count = sum(len(figs) for figs in figure_snippets)
                st.write(f"Saved {count} figures to `{images_dir}`")
                st.write(f"Metadata written to `{meta_path}`")
                # Display and provide download for composed UI preview
                with open(meta_path, 'r') as mf:
                    meta = json.load(mf)
                preview_path = meta.get('preview')
                if preview_path and os.path.exists(preview_path):
                    st.write(f"Preview saved to: `{preview_path}`")
                    st.image(preview_path, caption="Composed Diagram Preview", use_column_width=True)
                    with open(preview_path, "rb") as pf:
                        st.download_button(
                            label="Download Preview Image",
                            data=pf,
                            file_name=os.path.basename(preview_path),
                            mime="image/png"
                        )
                # Display parsed images as a horizontal carousel
                if parsed_images:
                    html = "<div style='display:flex; overflow-x:auto;'>"
                    for img in parsed_images:
                        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb)
                        buf = io.BytesIO()
                        pil_img.save(buf, format="PNG")
                        b64 = base64.b64encode(buf.getvalue()).decode()
                        html += f"<img src='data:image/png;base64,{b64}' width='300' style='margin-right:10px;'/>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                    # Display figure snippets page-wise with IDs
                    st.markdown("**Here are figures present:**")
                    # Global figure counter across pages
                    fig_counter = 1
                    for page_idx, figs in enumerate(figure_snippets):
                        if figs:
                            st.subheader(f"Page {page_idx+1}")
                            for fig_img in figs:
                                st.write(f"Figure {fig_counter}")
                                st.image(fig_img, width=200)
                                fig_counter += 1

    # PDF Splitting Tab (moved to index 2)
    with tabs[2]:
        st.header("PDF Splitting")
        uploaded_file = st.file_uploader("Upload Questions PDF", type=["pdf"], key="split_pdf")
        if uploaded_file is not None:
            file_key = f"{uploaded_file.name}_{uploaded_file.size}"
            if "processed_files" not in st.session_state:
                st.session_state.processed_files = {}
            if file_key not in st.session_state.processed_files:
                job_name = os.path.splitext(uploaded_file.name)[0]
                output_folder = init_job_logging(job_name)
                with st.spinner("Processing PDF..."):
                    process_pdf(uploaded_file, output_folder)
                st.session_state.processed_files[file_key] = output_folder
                st.success("PDF processed successfully!")
                st.write(f"Pages saved to: `{output_folder}`")
            else:
                output_folder = st.session_state.processed_files[file_key]
                st.info("PDF already processed!")
                st.write(f"Pages saved to: `{output_folder}`")
    # Extract Questions Tab (moved to index 3)
    with tabs[3]:
        st.header("Extract Questions")
        
        # Add radio button for mode selection
        extraction_mode = st.radio("Extraction Mode", ["Experiment Mode", "Bulk Test Mode"])
        
        if extraction_mode == "Experiment Mode":
            uploaded_extract_file = st.file_uploader("Upload PDF for Extraction", type=["pdf"], key="extract_pdf")
            if uploaded_extract_file is not None:
                # Read the uploaded file content
                pdf_bytes = uploaded_extract_file.read()
                
                st.write(f"File uploaded: `{uploaded_extract_file.name}`")
                
                if st.button("Extract Questions", key="extract_button"):
                    with st.spinner("Extracting questions..."):
                        # Create a temporary file to pass to generate_markdown_from_pdf
                        with st.empty():
                            # Rewind the file bytes
                            pdf_bytes = uploaded_extract_file.getvalue()
                            
                            # Save the file temporarily
                            with open(uploaded_extract_file.name, 'wb') as f:
                                f.write(pdf_bytes)
                            
                            # Generate markdown
                            markdown_path = generate_markdown_from_pdf(uploaded_extract_file.name)
                            
                            # Remove the temporary file
                            os.unlink(uploaded_extract_file.name)
                    
                    st.success("Extraction successful!")
                    
                    # Read markdown content
                    with open(markdown_path, 'r') as f:
                        markdown_content = f.read()
                    
                    # Log markdown using the original filename
                    filename_no_ext = os.path.splitext(uploaded_extract_file.name)[0]
                    saved_markdown_path = log_gemini_response(filename_no_ext, markdown_content)
                    
                    # Convert PDF to image
                    pdf_image = pdf_to_image(pdf_bytes)
                    
                    # Create two columns for side-by-side display
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("PDF Preview")
                        if pdf_image:
                            st.image(pdf_image, use_column_width=True)
                        else:
                            st.write("Could not generate PDF preview")
                    
                    with col2:
                        st.subheader("Extracted Markdown")
                        st.markdown(markdown_content)
                    
                    # Additional information
                    st.write(f"Markdown saved to: `{saved_markdown_path}`")
        
        elif extraction_mode == "Bulk Test Mode":
            uploaded_bulk_files = st.file_uploader("Upload Multiple PDFs for Bulk Extraction", type=["pdf"], accept_multiple_files=True, key="bulk_extract_pdfs")
            
            if uploaded_bulk_files:
                # Create containers for progress and results
                progress_container = st.empty()
                results_container = st.container()
                
                # Prepare a list to store results
                bulk_results = []
                
                # Use results_container to show results in real-time
                with results_container:
                    # Create a placeholder for dynamic results
                    results_placeholder = st.empty()
                
                # Iterate through PDFs sequentially
                for idx, uploaded_file in enumerate(uploaded_bulk_files, 1):
                    with progress_container:
                        st.info(f"Processing PDF {idx}/{len(uploaded_bulk_files)}: {uploaded_file.name}")
                    
                    # Read the uploaded file content
                    pdf_bytes = uploaded_file.getvalue()
                    
                    with st.spinner(f"Extracting questions from {uploaded_file.name}..."):
                        # Save the file temporarily
                        with open(uploaded_file.name, 'wb') as f:
                            f.write(pdf_bytes)
                        
                        try:
                            # Generate markdown
                            markdown_path = generate_markdown_from_pdf(uploaded_file.name)
                            
                            # Remove the temporary file
                            os.unlink(uploaded_file.name)
                            
                            # Read markdown content
                            with open(markdown_path, 'r') as f:
                                markdown_content = f.read()
                            
                            # Log markdown using the original filename
                            filename_no_ext = os.path.splitext(uploaded_file.name)[0]
                            saved_markdown_path = log_gemini_response(filename_no_ext, markdown_content)
                            
                            # Convert PDF to image
                            pdf_image = pdf_to_image(pdf_bytes)
                            
                            # Create result for this PDF
                            result = {
                                'filename': uploaded_file.name,
                                'markdown_path': saved_markdown_path,
                                'markdown_content': markdown_content,
                                'pdf_image': pdf_image
                            }
                            
                            # Add to results list
                            bulk_results.append(result)
                            
                            # Update progress
                            with progress_container:
                                st.success(f"Extracted questions from {uploaded_file.name}")
                            
                            # Render results in real-time
                            with results_container:
                                st.header(f"Bulk Extraction Results (Processed: {len(bulk_results)}/{len(uploaded_bulk_files)})")
                                
                                # Create two columns for side-by-side display
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.subheader("PDF Preview")
                                    if result['pdf_image']:
                                        st.image(result['pdf_image'], use_column_width=True)
                                    else:
                                        st.write("Could not generate PDF preview")
                                
                                with col2:
                                    st.subheader("Extracted Markdown")
                                    st.markdown(result['markdown_content'])
                                
                                # Additional information
                                st.write(f"Markdown saved to: `{result['markdown_path']}`")
                                
                                # Add a divider between results
                                st.markdown("---")
                        
                        except Exception as e:
                            # Handle extraction errors
                            with progress_container:
                                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                
                # Final summary
                with progress_container:
                    st.success(f"Bulk extraction completed. Processed {len(bulk_results)}/{len(uploaded_bulk_files)} PDFs successfully.") 
    
    # Full PDF Question Extraction Tab
    with tabs[4]:
        st.header("Full PDF Question Extraction")
        st.markdown("""
        This feature extracts **ONLY the questions** from a complete CBSE Mathematics exam paper, 
        excluding all instructions, diagrams, and metadata. Perfect for creating question banks.
        """)
        
        uploaded_full_pdf = st.file_uploader(
            "Upload Complete PDF Question Paper", 
            type=["pdf"], 
            key="full_pdf_extraction"
        )
        
        if uploaded_full_pdf is not None:
            st.write(f"File uploaded: `{uploaded_full_pdf.name}`")
            
            if st.button("Extract All Questions", key="extract_all_questions_button"):
                with st.spinner("Extracting questions from the complete PDF..."):
                    try:
                        # Create a temporary file to pass to extract_questions_from_pdf
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                            tmp_file.write(uploaded_full_pdf.getvalue())
                            tmp_file_path = tmp_file.name
                        
                        # Extract questions using the new function
                        questions_path, raw_response_path = extract_questions_from_pdf(tmp_file_path)
                        
                        # Clean up temporary file
                        os.unlink(tmp_file_path)
                        
                        st.success("✅ Questions extracted successfully!")
                        
                        # Read the extracted questions and raw response
                        with open(questions_path, 'r', encoding='utf-8') as f:
                            questions_content = f.read()
                        
                        with open(raw_response_path, 'r', encoding='utf-8') as f:
                            raw_response_content = f.read()
                        
                        # Create tabs for different views
                        result_tabs = st.tabs(["📝 Extracted Questions", "🔍 Raw Response", "📁 File Info"])
                        
                        with result_tabs[0]:
                            st.subheader("📝 Extracted Questions")
                            st.markdown("**Clean questions extracted from the PDF:**")
                            
                            # Display the extracted questions in a scrollable text area
                            st.text_area(
                                "Extracted Questions Preview",
                                questions_content,
                                height=400,
                                key="full_questions_preview"
                            )
                            
                            # Provide download button
                            st.download_button(
                                label="⬇️ Download Extracted Questions",
                                data=questions_content,
                                file_name=f"extracted_questions_{uploaded_full_pdf.name.replace('.pdf', '.md')}",
                                mime="text/markdown",
                                key="download_full_questions"
                            )
                        
                        with result_tabs[1]:
                            st.subheader("🔍 Raw Response from Gemini")
                            st.markdown("**Complete response including analysis and reasoning:**")
                            
                            # Display the raw response in a scrollable text area
                            st.text_area(
                                "Raw Response Preview",
                                raw_response_content,
                                height=400,
                                key="raw_response_preview"
                            )
                            
                            # Provide download button for raw response
                            st.download_button(
                                label="⬇️ Download Raw Response",
                                data=raw_response_content,
                                file_name=f"raw_response_{uploaded_full_pdf.name.replace('.pdf', '.txt')}",
                                mime="text/plain",
                                key="download_raw_response"
                            )
                        
                        with result_tabs[2]:
                            st.subheader("📁 File Information")
                            st.markdown("**Generated Files:**")
                            st.write(f"📄 **Extracted Questions:** `{questions_path}`")
                            st.write(f"📄 **Raw Response:** `{raw_response_path}`")
                            
                            # Show file sizes
                            questions_size = os.path.getsize(questions_path)
                            raw_size = os.path.getsize(raw_response_path)
                            
                            st.write(f"📊 **Questions File Size:** {questions_size:,} bytes")
                            st.write(f"📊 **Raw Response File Size:** {raw_size:,} bytes")
                            
                            # Show character counts
                            st.write(f"📝 **Questions Character Count:** {len(questions_content):,}")
                            st.write(f"📝 **Raw Response Character Count:** {len(raw_response_content):,}")
                        
                    except Exception as e:
                        st.error(f"❌ Error extracting questions: {str(e)}")
                        st.error("Please check the PDF format and try again.")
    
    # Map Diagrams Tab (moved to index 1)
    with tabs[1]:
        st.header("Map Diagrams")
        # Upload a single diagram image
        uploaded_img = st.file_uploader(
            "Upload Diagram Image", type=["png", "jpg", "jpeg"], key="map_image"
        )
        # Upload the corresponding PDF for mapping context
        uploaded_pdf = st.file_uploader(
            "Upload PDF for Mapping", type=["pdf"], key="map_pdf"
        )
        if st.button("Submit Mapping", key="map_submit"):
            if uploaded_img and uploaded_pdf:
                # Generate mapping via Gemini
                with st.spinner("Generating diagram mapping..."):
                    # Save uploaded files to temporary paths
                    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    tmp_pdf.write(uploaded_pdf.read())
                    tmp_pdf.flush()
                    tmp_pdf.close()
                    tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_img.name)[1] or ".png")
                    tmp_img.write(uploaded_img.read())
                    tmp_img.flush()
                    tmp_img.close()
                    try:
                        mapping_path, raw_text = generate_diagram_mapping(tmp_pdf.name, tmp_img.name)
                        # Display full raw LLM response
                        st.subheader("LLM Reasoning and Output:")
                        st.text_area("Raw Response", raw_text, height=300)
                        st.success("Mapping generated successfully!")
                        # Display mapping JSON
                        with open(mapping_path, 'r', encoding='utf-8') as mf:
                            mapping_data = json.load(mf)
                        st.subheader("Parsed Mapping JSON:")
                        st.json(mapping_data)
                        # Download button for mapping JSON
                        with open(mapping_path, 'rb') as mf:
                            st.download_button(
                                label="Download Mapping JSON",
                                data=mf,
                                file_name=os.path.basename(mapping_path),
                                mime="application/json"
                            )
                    except Exception as e:
                        st.error(f"Error generating mapping: {str(e)}")
                    finally:
                        # Clean up temp files
                        try:
                            os.unlink(tmp_pdf.name)
                        except:
                            pass
                        try:
                            os.unlink(tmp_img.name)
                        except:
                            pass
            else:
                st.error("Please upload both an image and a PDF before submitting.")
    # Extract Marks Tab
    with tabs[5]:
        st.header("Extract Marks")
        uploaded_marks_pdf = st.file_uploader("Upload PDF for Marks Extraction", type=["pdf"], key="marks_pdf")
        if st.button("Extract Marks", key="marks_submit"):
            if uploaded_marks_pdf:
                with st.spinner("Generating marks mapping..."):
                    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    tmp_pdf.write(uploaded_marks_pdf.read())
                    tmp_pdf.flush()
                    tmp_pdf.close()
                    try:
                        mapping_path, raw_text = generate_marks_mapping(tmp_pdf.name)
                        st.subheader("LLM Reasoning and Output:")
                        st.text_area("Raw Response", raw_text, height=300)
                        st.subheader("Parsed Marks JSON:")
                        with open(mapping_path, 'r', encoding='utf-8') as mf:
                            mapping_data = json.load(mf)
                        st.json(mapping_data)
                        with open(mapping_path, 'rb') as mf:
                            st.download_button(
                                label="Download Marks JSON",
                                data=mf,
                                file_name=os.path.basename(mapping_path),
                                mime="application/json"
                            )
                    except Exception as e:
                        st.error(f"Error generating marks mapping: {str(e)}")
                    finally:
                        try:
                            os.unlink(tmp_pdf.name)
                        except:
                            pass
            else:
                st.error("Please upload a PDF before submitting.")
    
    # End-to-End Tab
    with tabs[6]:
        st.header("🚀 End-to-End Processing")
        st.markdown("""
        This tab runs the complete CBSE question paper processing pipeline:
        1. **Diagram Extraction** - Extract diagrams from the PDF
        2. **Diagram Mapping** - Map diagrams to questions using Gemini
        3. **Marks Extraction** - Extract marks allocation using Gemini
        4. **PDF Splitting & Text Extraction** - Split PDF and extract text from each page
        5. **Full PDF Question Extraction** - Extract all questions from the complete PDF
        """)
        
        uploaded_e2e_file = st.file_uploader(
            "Upload Question Paper PDF", type=["pdf"], key="e2e_pdf"
        )
        
        if uploaded_e2e_file is not None:
            st.success(f"✅ File uploaded: {uploaded_e2e_file.name}")
            
            # Import the end-to-end processing functions
            from end_to_end import (
                run_end_to_end_processing, 
                run_step_1, 
                run_step_2, 
                run_step_3, 
                run_step_4,
                run_step_5
            )
            
            # Create columns for buttons
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔄 Complete Pipeline")
                if st.button("🚀 Run End-to-End Processing", key="run_e2e", type="primary"):
                    # Initialize progress containers
                    progress_container = st.empty()
                    results_container = st.container()
                    
                    def step_callback(message, status):
                        if status == "success":
                            progress_container.success(message)
                        elif status == "error":
                            progress_container.error(message)
                        elif status == "warning":
                            progress_container.warning(message)
                        else:
                            progress_container.info(message)
                    
                    # Run the complete pipeline
                    results = run_end_to_end_processing(uploaded_e2e_file, step_callback)
                    
                    # Display results
                    with results_container:
                        if results['success']:
                            st.success("🎉 End-to-End Processing Complete!")
                            
                            # Display final summary
                            st.subheader("📊 Final Results Summary")
                            final_outputs = results['final_outputs']
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Total Diagrams", final_outputs['total_diagrams'])
                                st.metric("Total Pages", final_outputs['total_pages'])
                            with col_b:
                                st.metric("Markdown Files", len(final_outputs['markdown_files']))
                                st.metric("Processing Steps", 5)
                            
                            # Show diagram preview if available
                            if 'step1' in results['step_results'] and results['step_results']['step1']['meta_path']:
                                import json
                                try:
                                    with open(results['step_results']['step1']['meta_path'], 'r') as f:
                                        meta = json.load(f)
                                    preview_path = meta.get('preview')
                                    
                                    if preview_path and os.path.exists(preview_path):
                                        st.subheader("📸 Extracted Diagrams")
                                        st.image(preview_path, caption="All Diagrams with Page and Figure Numbers", use_column_width=True)
                                        
                                        with open(preview_path, "rb") as pf:
                                            st.download_button(
                                                label="⬇️ Download Diagrams Preview",
                                                data=pf,
                                                file_name=os.path.basename(preview_path),
                                                mime="image/png",
                                                key="e2e_preview_download"
                                            )
                                except:
                                    pass
                            
                            # Display file paths
                            st.subheader("📁 Generated Files")
                            if final_outputs['diagram_mapping']:
                                st.write(f"📊 Diagram Mapping: `{final_outputs['diagram_mapping']}`")
                            if final_outputs['marks_mapping']:
                                st.write(f"📝 Marks Mapping: `{final_outputs['marks_mapping']}`")
                            if final_outputs['markdown_files']:
                                st.write(f"📄 Markdown Files: {len(final_outputs['markdown_files'])} files generated")
                            if final_outputs['full_pdf_questions']:
                                st.write(f"📋 Full PDF Questions: `{final_outputs['full_pdf_questions']}`")
                            if final_outputs['full_pdf_raw_response']:
                                st.write(f"🔍 Full PDF Raw Response: `{final_outputs['full_pdf_raw_response']}`")
                            
                            # Display any errors
                            if results['errors']:
                                st.subheader("⚠️ Warnings/Errors")
                                for error in results['errors']:
                                    st.warning(error)
                            
                        else:
                            st.error("❌ End-to-End Processing Failed")
                            st.subheader("🐛 Error Details")
                            for error in results['errors']:
                                st.error(error)
            
            with col2:
                st.subheader("🔍 Individual Steps (Debug)")
                st.markdown("*Use these buttons to test individual steps:*")
                
                # Step 1: Diagram Extraction
                if st.button("Step 1: Extract Diagrams", key="step1_btn"):
                    with st.spinner("Extracting diagrams..."):
                        try:
                            result = run_step_1(uploaded_e2e_file)
                            if result['success']:
                                st.success(f"✅ Step 1 Complete: {result['total_figures']} diagrams extracted")
                                
                                # Show preview image instead of JSON
                                if result['meta_path'] and os.path.exists(result['meta_path']):
                                    import json
                                    with open(result['meta_path'], 'r') as f:
                                        meta = json.load(f)
                                    preview_path = meta.get('preview')
                                    
                                    if preview_path and os.path.exists(preview_path):
                                        st.subheader("📸 Extracted Diagrams Preview")
                                        st.image(preview_path, caption="Diagrams with Page and Figure Numbers", use_column_width=True)
                                        
                                        # Show download button
                                        with open(preview_path, "rb") as pf:
                                            st.download_button(
                                                label="⬇️ Download Preview Image",
                                                data=pf,
                                                file_name=os.path.basename(preview_path),
                                                mime="image/png"
                                            )
                                    else:
                                        st.warning("No preview image available")
                                
                                # Show summary info
                                st.info(f"📊 Summary: {result['total_figures']} diagrams extracted from {len(result['figure_snippets'])} pages")
                                
                                # Option to show detailed JSON for debugging
                                with st.expander("🔍 Show Detailed Results (Debug)"):
                                    st.json(result)
                            else:
                                st.error(f"❌ Step 1 Failed: {result['error']}")
                        except Exception as e:
                            st.error(f"❌ Step 1 Error: {str(e)}")
                
                # Step 2: Diagram Mapping
                if st.button("Step 2: Map Diagrams", key="step2_btn"):
                    with st.spinner("Mapping diagrams..."):
                        try:
                            result = run_step_2(uploaded_e2e_file)
                            if result['success']:
                                st.success("✅ Step 2 Complete: Diagram mapping generated")
                                st.json(result)
                            else:
                                st.error(f"❌ Step 2 Failed: {result['error']}")
                        except Exception as e:
                            st.error(f"❌ Step 2 Error: {str(e)}")
                
                # Step 3: Marks Extraction
                if st.button("Step 3: Extract Marks", key="step3_btn"):
                    with st.spinner("Extracting marks..."):
                        try:
                            result = run_step_3(uploaded_e2e_file)
                            if result['success']:
                                st.success("✅ Step 3 Complete: Marks mapping generated")
                                st.json(result)
                            else:
                                st.error(f"❌ Step 3 Failed: {result['error']}")
                        except Exception as e:
                            st.error(f"❌ Step 3 Error: {str(e)}")
                
                # Step 4: PDF Splitting & Text Extraction
                if st.button("Step 4: Split PDF & Extract Text", key="step4_btn"):
                    with st.spinner("Splitting PDF and extracting text..."):
                        try:
                            result = run_step_4(uploaded_e2e_file)
                            if result['success']:
                                st.success(f"✅ Step 4 Complete: {result['successful_pages']}/{result['total_pages']} pages processed")
                                st.json(result)
                            else:
                                st.error(f"❌ Step 4 Failed: {result['error']}")
                        except Exception as e:
                            st.error(f"❌ Step 4 Error: {str(e)}")
                
                # Step 5: Full PDF Question Extraction
                if st.button("Step 5: Extract All Questions", key="step5_btn"):
                    with st.spinner("Extracting all questions from PDF..."):
                        try:
                            result = run_step_5(uploaded_e2e_file)
                            if result['success']:
                                st.success("✅ Step 5 Complete: Full PDF question extraction completed")
                                
                                # Read and display the extracted questions
                                with open(result['questions_path'], 'r', encoding='utf-8') as f:
                                    questions_content = f.read()
                                
                                with open(result['raw_response_path'], 'r', encoding='utf-8') as f:
                                    raw_response_content = f.read()
                                
                                # Create tabs for different views
                                step5_tabs = st.tabs(["📝 Extracted Questions", "🔍 Raw Response"])
                                
                                with step5_tabs[0]:
                                    st.subheader("📝 Extracted Questions")
                                    st.text_area(
                                        "Questions Preview",
                                        questions_content,
                                        height=300,
                                        key="step5_questions_preview"
                                    )
                                    
                                    # Download button
                                    st.download_button(
                                        label="⬇️ Download Questions",
                                        data=questions_content,
                                        file_name=os.path.basename(result['questions_path']),
                                        mime="text/markdown",
                                        key="step5_download_questions"
                                    )
                                
                                with step5_tabs[1]:
                                    st.subheader("🔍 Raw Response")
                                    st.text_area(
                                        "Raw Response Preview",
                                        raw_response_content,
                                        height=300,
                                        key="step5_raw_preview"
                                    )
                                    
                                    # Download button
                                    st.download_button(
                                        label="⬇️ Download Raw Response",
                                        data=raw_response_content,
                                        file_name=os.path.basename(result['raw_response_path']),
                                        mime="text/plain",
                                        key="step5_download_raw"
                                    )
                                
                                # Show file paths
                                st.info(f"📁 Files saved: Questions: `{result['questions_path']}`, Raw Response: `{result['raw_response_path']}`")
                                
                            else:
                                st.error(f"❌ Step 5 Failed: {result['error']}")
                        except Exception as e:
                            st.error(f"❌ Step 5 Error: {str(e)}")
        
        else:
            st.info("👆 Please upload a question paper PDF to begin processing.")
    
    # Question Cards Tab
    with tabs[7]:
        st.header("🎴 Question Cards")
        st.markdown("*Generate beautiful question cards with integrated diagrams and marks using full PDF question extraction*")
        
        # PDF upload
        uploaded_file = st.file_uploader(
            "Upload CBSE Mathematics Question Paper",
            type=['pdf'],
            help="Upload a PDF file to generate question cards",
            key="question_cards_upload"
        )
        
        if uploaded_file is not None:
            # Display file info
            st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            # Processing options
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown("**Processing Options:**")
                use_existing_data = st.checkbox(
                    "Use existing processed data (if available)",
                    value=True,
                    help="Check if you've already processed this PDF and want to use existing results"
                )
            
            with col2:
                if st.button("🎴 Generate Question Cards", key="generate_cards_btn"):
                    with st.spinner("Processing PDF and generating question cards..."):
                        try:
                            # Extract filename without extension
                            pdf_filename = os.path.splitext(uploaded_file.name)[0]
                            
                            # Check if we should use existing data or process fresh
                            if use_existing_data:
                                # Try to use existing processed data
                                try:
                                    generate_question_cards(pdf_filename)
                                    st.success("✅ Question cards generated using existing data!")
                                except Exception as e:
                                    st.warning(f"Could not use existing data: {str(e)}")
                                    st.info("🔄 Processing PDF from scratch...")
                                    
                                    # Process PDF from scratch
                                    process_pdf_and_generate_cards(uploaded_file)
                            else:
                                # Process PDF from scratch
                                process_pdf_and_generate_cards(uploaded_file)
                                
                        except Exception as e:
                            st.error(f"Error generating question cards: {str(e)}")
                            st.info("Please check the PDF format and try again.")
        else:
            st.info("👆 Please upload a PDF file to generate question cards.")
            
            # Show instructions
            with st.expander("📋 Instructions"):
                st.markdown("""
                **How to use Question Cards:**
                
                1. **Upload PDF**: Click the upload button and select your CBSE Mathematics question paper
                2. **Choose Processing Option**:
                   - ✅ **Use existing data**: If you've already processed this PDF, the system will use cached results
                   - ❌ **Process from scratch**: Forces complete reprocessing (takes longer but ensures fresh results)
                3. **Generate Cards**: Click the button to start processing and card generation
                
                **What happens during processing:**
                - 🔍 **Step 1**: Extract diagrams from the PDF
                - 🔗 **Step 2**: Map diagrams to questions
                - 📊 **Step 3**: Extract marks information
                - 📝 **Step 5**: Extract all questions using full PDF analysis
                - 🎴 **Final**: Generate beautiful question cards with integrated data
                
                **Expected processing time:**
                - Using existing data: ~10-30 seconds
                - Processing from scratch: ~2-5 minutes (depending on PDF size)
                """)
            
            # Show sample card preview
            with st.expander("👀 Sample Card Preview"):
                st.markdown("""
                **Sample Question Card Features:**
                
                🎨 **Visual Design**:
                - Color-coded question types (MCQ, Case Study, etc.)
                - Clean, professional layout
                - Responsive design
                
                📊 **Content Display**:
                - Question number and text
                - Associated diagrams (if any)
                - Marks allocation
                - Internal choice handling
                
                🔍 **Interactive Features**:
                - Filter by question type
                - Search functionality
                - Expandable sections
                - Export capabilities
                """)
            
            # Show troubleshooting tips
            with st.expander("🔧 Troubleshooting"):
                st.markdown("""
                **Common Issues:**
                
                1. **"Could not use existing data"**: This means the PDF hasn't been processed before
                   - Solution: Uncheck "Use existing data" to process from scratch
                
                2. **"Processing takes too long"**: Full processing can take 2-5 minutes
                   - Solution: Be patient, or use existing data if available
                
                3. **"No questions found"**: The PDF might not be a proper CBSE format
                   - Solution: Ensure your PDF is a CBSE Mathematics question paper
                
                4. **"Missing diagrams"**: Diagrams might not be detected properly
                   - Solution: Check if diagrams are clear and well-defined in the PDF
                
                **Tips for best results:**
                - Use high-quality PDF files
                - Ensure text is searchable (not scanned images)
                - CBSE Mathematics format works best
                - Check that questions are numbered properly
                """)
            
            # Show sample card preview  
            with st.expander("👀 Sample Card Preview"):
                st.markdown("""
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 5px solid #1f77b4;">
                    <h3 style="margin: 0; color: #1f77b4;">🔘 Question 1</h3>
                    <div style="background-color: white; padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <strong>Type:</strong> MCQ &nbsp;&nbsp;&nbsp; <strong>Marks:</strong> 1 mark
                    </div>
                    <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <h4 style="color: #333; margin-top: 0;">Question Text:</h4>
                        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
                            The LCM of smallest two digit composite number and smallest composite number is:<br>
                            (A) 12<br>
                            (B) 4<br>
                            (C) 20<br>
                            (D) 44
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)