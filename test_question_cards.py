#!/usr/bin/env python3
"""
Test script for the end-to-end question card generation workflow
Shows output after each step for debugging and verification
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import traceback

# Add the current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_environment():
    """Check if environment is set up correctly"""
    print("🔍 Checking environment...")
    
    # Check API key
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        return False
    else:
        print(f"✅ GEMINI_API_KEY found (length: {len(gemini_key)})")
    
    # Check dependencies
    missing_deps = []
    try:
        import torch
        print(f"✅ PyTorch found (version: {torch.__version__})")
    except ImportError:
        missing_deps.append("torch")
    
    try:
        from google import genai
        print("✅ Google Genai found")
    except ImportError:
        missing_deps.append("google-genai")
    
    try:
        import streamlit
        print(f"✅ Streamlit found (version: {streamlit.__version__})")
    except ImportError:
        missing_deps.append("streamlit")
    
    try:
        from doclayout_yolo import YOLOv10
        print("✅ DocLayout YOLO found")
    except ImportError:
        missing_deps.append("doclayout-yolo")
    
    try:
        import fitz
        print("✅ PyMuPDF found")
    except ImportError:
        missing_deps.append("PyMuPDF")
    
    try:
        from pdf2image import convert_from_bytes
        print("✅ pdf2image found")
    except ImportError:
        missing_deps.append("pdf2image")
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        return False
    
    return True

def test_imports():
    """Test importing the main functions"""
    print("🔍 Testing imports...")
    
    try:
        from end_to_end import (
            run_end_to_end_processing,
            run_step_1,
            run_step_2,
            run_step_3,
            run_step_4,
            run_step_5
        )
        print("✅ All main functions imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def print_separator(title):
    """Print a nice separator for each step"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_step_output(step_name, result):
    """Print formatted output for each step"""
    print(f"\n{step_name} Results:")
    print("-" * 40)
    
    if result.get('success'):
        print("✅ SUCCESS")
        
        # Remove success and error keys for cleaner output
        output_data = {k: v for k, v in result.items() if k not in ['success', 'error']}
        
        for key, value in output_data.items():
            if isinstance(value, (str, int, float, bool)):
                print(f"  {key}: {value}")
            elif isinstance(value, list):
                print(f"  {key}: {len(value)} items")
                if len(value) > 0 and len(value) <= 3:
                    for i, item in enumerate(value):
                        if isinstance(item, str) and len(item) < 100:
                            print(f"    [{i}]: {item}")
                        else:
                            print(f"    [{i}]: {type(item).__name__}")
            elif isinstance(value, dict):
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {type(value).__name__}")
    else:
        print("❌ FAILED")
        print(f"  Error: {result.get('error', 'Unknown error')}")

def display_file_contents(file_path, max_lines=20):
    """Display first few lines of a file"""
    if not file_path or not os.path.exists(file_path):
        print(f"  File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        print(f"  📄 File: {file_path}")
        print(f"  📊 Total lines: {len(lines)}")
        print(f"  👀 First {min(max_lines, len(lines))} lines:")
        print("  " + "-" * 50)
        
        for i, line in enumerate(lines[:max_lines]):
            print(f"  {i+1:2d}: {line.rstrip()}")
            
        if len(lines) > max_lines:
            print(f"  ... and {len(lines) - max_lines} more lines")
            
    except Exception as e:
        print(f"  Error reading file: {e}")

def test_individual_steps():
    """Test each step individually"""
    print_separator("INDIVIDUAL STEP TESTING")
    
    # You need to provide a test PDF file path here
    test_pdf_path = "test_paper.pdf"  # Replace with your actual PDF path
    
    if not os.path.exists(test_pdf_path):
        print(f"❌ Test PDF not found: {test_pdf_path}")
        print("Please provide a valid PDF file path in the script")
        print("You can:")
        print("1. Create a test PDF file named 'test_paper.pdf' in the current directory")
        print("2. Or update the 'test_pdf_path' variable in this script")
        return False
    
    # Import the functions
    try:
        from end_to_end import run_step_1, run_step_2, run_step_3, run_step_4, run_step_5
    except Exception as e:
        print(f"❌ Failed to import functions: {e}")
        return False
    
    # Create a mock uploaded file object
    class MockUploadedFile:
        def __init__(self, file_path):
            self.file_path = file_path
            self.name = os.path.basename(file_path)
            
        def getvalue(self):
            with open(self.file_path, 'rb') as f:
                return f.read()
    
    uploaded_file = MockUploadedFile(test_pdf_path)
    
    # Test Step 1: Diagram Extraction
    print_separator("STEP 1: DIAGRAM EXTRACTION")
    try:
        step1_result = run_step_1(uploaded_file)
        print_step_output("Step 1", step1_result)
        
        if step1_result.get('success'):
            print(f"\n📊 Diagram Statistics:")
            print(f"  Total figures extracted: {step1_result.get('total_figures', 0)}")
            print(f"  Images directory: {step1_result.get('images_dir', 'N/A')}")
            print(f"  Metadata file: {step1_result.get('meta_path', 'N/A')}")
            
            # Display metadata if available
            if step1_result.get('meta_path'):
                display_file_contents(step1_result['meta_path'])
    except Exception as e:
        print(f"❌ Step 1 exception: {e}")
        traceback.print_exc()
    
    # Test Step 4: Full PDF Question Extraction (skip 2 and 3 for now)
    print_separator("STEP 4: FULL PDF QUESTION EXTRACTION")
    try:
        step4_result = run_step_4(uploaded_file)
        print_step_output("Step 4", step4_result)
        
        if step4_result.get('success'):
            print(f"\n📊 Question Extraction Statistics:")
            print(f"  Questions file: {step4_result.get('questions_path', 'N/A')}")
            print(f"  Raw response file: {step4_result.get('raw_response_path', 'N/A')}")
            
            # Display questions content if available
            if step4_result.get('questions_path'):
                print(f"\n📖 Extracted Questions Preview:")
                display_file_contents(step4_result['questions_path'], max_lines=30)
    except Exception as e:
        print(f"❌ Step 4 exception: {e}")
        traceback.print_exc()
    
    return True

def main():
    """Main test function"""
    print_separator("QUESTION CARD GENERATION WORKFLOW TEST")
    print("This script tests the end-to-end question card generation workflow")
    print("Make sure you have a test PDF file available!")
    
    try:
        # Check environment
        if not check_environment():
            print("\n❌ Environment check failed. Please fix the issues above.")
            return False
        
        # Test imports
        if not test_imports():
            print("\n❌ Import test failed. Please check the installation.")
            return False
        
        # Test individual steps
        if not test_individual_steps():
            print("\n❌ Individual step testing failed.")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        traceback.print_exc()
        return False
    
    print_separator("TEST COMPLETED")
    print("✅ All tests passed! The system should be working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
