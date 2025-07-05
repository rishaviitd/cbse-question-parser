import os
import streamlit as st
from utils import process_pdf, extract_questions_from_folder
from logs.logger import init_job_logging, log_diagram_snippets, log_gemini_response
import tempfile
from api.gemini import generate_markdown_from_pdf
from logic.diagram_extraction import extract_diagrams_from_pdf
from pdf2image import convert_from_bytes
import io, base64
import cv2
from PIL import Image
import json

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
    tabs = st.tabs(["Extract Diagrams", "PDF Splitting", "Extract Questions"])

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

    # PDF Splitting Tab
    with tabs[1]:
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
    # Extract Questions Tab
    with tabs[2]:
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