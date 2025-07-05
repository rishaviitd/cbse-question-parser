Functionality-1;
<start>

# UI

## Page Extraction and Splitting

- The user interface will feature a single file uploader labeled 'Upload Questions PDF'.
- Upon selecting a PDF, the system will automatically begin processing and display a status message.
- A success message will be shown once the process is complete. There will be no download button.

## PDF question extraction using Gemini

Just add a button named "Extract Questions" that will be become visible after the the PDF was extraction

# Implementation

## Page Extraction and Splitting

- After a PDF is uploaded, the system reads the entire document.
- It will then go through the document page by page, from the first to the last.
- Each page is extracted and saved as a brand new, single-page PDF file (use pymupdf).

- To maintain the correct order, the output files will be named sequentially (e.g., page_001.pdf, page_002.pdf, etc.).

## PDF question extraction using Gemini

Refer the api.instructions.md in the api/ folder

# Logging

- The generated single-page PDF files are the primary output of this application.
- For each uploaded PDF, a new, unique sub-folder will be created inside the `logs/pages/` directory to keep different jobs separate.
- On completion of the process, all the newly created single-page PDFs will be saved into that unique sub-folder on the server.
  <end>

Functionality-2:
<start>

#Extracting the questions from the individual PDF

## Implementation

Use the prompt from the api/prompt/maths.py and use the structured output JSON schema from the api/response/maths.json for generating the strucutured output while sending the request to gemini-2.5-flash-lite-preview-06-1, also the input will be a pdf file.

##UI
Then show the response in the streamlit UI

<end>
