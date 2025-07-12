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

!!!! Context Project !!!!
Genral idea of the task:

The input will be a pdf which is a CBSE mathematics question paper. which contains matemetics question paper with typical mathematics quesitons that are present normally. like MCQ, Assertion reasoning, Subjective question with internal choice and case study type questions with subparts and question and subparts having an internal choice.

Now I want the final ouput to be

question number
question text
diagram associated to the question
marks associated to the question

shown in a beaitiful card

now this task is not that easy.
why because the LLM are only good if you first break the task and give them subproblems to solve.

So what I did is I first broke the problem to [X] key parts, here are those step by step with their description, function, input and output explained.

first step is-
**Extracting diagrams**
decription:
the input will be a pdf file. and the ouput is a preview image [I have attached one of the correctly genrated preview image]. which is very nicely organized into page numbers and each figure is given as figure <number>. and it's saved in the logs/diagrams/previews.

Now why this is preview image is genrated and saved?

Since the preview image only contain which figure <number> is present in which page. We don't have a way to map the diagrams to their respective questions.

that's why I generated this preview image so that this will be send to gemini LLM with the orignal pdf from which the diagrams were extracted.

that makes this our step 2:

so in short step 2 is input [preview-image+original-pdf] and the output will be
{
"figure-1": {
"question_identifier": "18",
"choice_location": "null"
},
"figure-2": {
"question_identifier": "24",
"choice_location": "null"
},
"figure-3": {
"question_identifier": "30",
"choice_location": "first"
},
"figure-4": {
"question_identifier": "30",
"choice_location": "second"
},
}

let me explain the varibles here
figure number is coming from the figure number mentioned in the preview image for a particulat figure.
question identifier is the main question identifier with which this diagram is linked to.

choice location is a catchy one. see in cbse boards there are questions that have internal choice now there can be a case that the choice-1 has a diagarm or choice 2 have a diagram.

let's talk about the first case only choice-1 has diagram
"figure-3": {
"question_identifier": "30",
"choice_location": "first"
},
let's talk about the first case only choice-2 has diagram
"figure-4": {
"question_identifier": "30",
"choice_location": "second"
},

now both has diagrams will be [two different figure will be mapped with the same main question identifer]

"figure-5": {
"question_identifier": "30",
"choice_location": "first"
},

"figure-6": {
"question_identifier": "30",
"choice_location": "second"
},

Now with that what we have the quetion and diagram mapping ready

This brings us to the next step. extracting the questions from the orignal pdf becasue we will need the question text as well.

Okay so step3 input will be the orignal pdf of the question paper and the ouput will be text which sometimes includes the reasoning ouput+final output in markdown code blocks or just markdown codeblocks [```markdown```]

Here is what the ouput looks like-
[first will be the reasoning steps]
**Step 1: Initial Document Analysis**
I can see 6 total pages with 38 distinct questions numbered from 1 to 38. The document contains 5 sections (A, B, C, D, E) with multiple question types including MCQs, assertion-reason, case studies, and multi-part questions.

**Step 2: Question Inventory and Mapping**
I will now scan the entire document to create a complete question inventory:

- Questions 1-18: Section A (MCQs)
- Questions 19-20: Section A (Assertion-Reason)
- Questions 21-25: Section B (2 marks each)
  ........... [truncated since this much text is enough to set the context]

[then the final ouput contains the markdown]

````markdown
1. The LCM of smallest two digit composite number and smallest composite number is:
   (A) 12
   (B) 4
   (C) 20
   (D) 44
   [####]
   .... till 30 [I intentionally removed other questions since these were enough to let you know about the output]
2. Prove that sin θ / (cos θ + sin θ - 1) + cos θ / (sin θ - cos θ + 1) = sec θ - tan θ
   [####]

3. If the median of the following distribution is 46, find the missing frequencies p and q if the total frequency is 230.
   [####]

4. Rasheed got a playing top (lattu) as his birthday present, which surprisingly had no colour on it. He wanted to colour it with his crayons. The top is shaped like a cone surmounted by a hemisphere (see below figure). The entire top is 5 cm in height and the diameter of the top is 3.5 cm. Find the area he has to colour. (Take π = 22/7)
   [%OR%]
   A solid toy is in the form of a hemisphere surmounted by a right circular cone. The height of the cone is 2 cm and the diameter of the base is 4 cm. Determine the volume of the toy. If a right circular cylinder circumscribes the toy, find the difference of the volumes of the cylinder and the toy. (Take π = 3.14)
   [####]

Now as you can see that questions are nicely separated by [####] after every question end. so if someone what to count the number of quesitons then just [####] number can be counted it will give the number of questions.

you could also see that
[%OR%] are also present wherever there is internal choice present

since here we have separated the questions with [####] we can now separate the main quesitons text. and since we have also tagged the "OR" {internal choice} to [%OR%] so we can also separate the internal choice quesitons as well but there is still an missing piece.

consider this question 38. Aditya, Ritesh and Damodar are fast friend since childhood. They always want to sit in a row in the classroom. But teacher doesn't allow them and rotate the seats row-wise everyday. Ritesh is very good in maths and he does distance calculation everyday. He consider the centre of class as origin and marks their position on a paper in a co-ordinate system. One day Ritesh make the following diagram of their seating position marked Aditya as A, Ritesh as B and Damodar as C.
(i) What is the distance between A and B ? [1]
(ii) What is the distance between B and C ? [1]
(iii) A point D lies on the line segment between points A and B such that AD :DB = 4 : 3 . What are the the coordinates of point D? [2]
[%OR%]
(iii) If the point P(k, 0) divides the line segment joining the points A(2, –2) and B(–7, 4) in the ratio 1: 2, then find the value of k [2]
[####]
here also there is an internal choice identifier but here since this is a case study based question I won't be splitting it into separate quetions because if I separate it then the context will be lost because questions of case study type have context on the previous questions and also the question comprehension.

This brings us to the next step:

the problem at hand is how we can categorize the questions as MCQ/Internal Choice/Case Study/ Assertion Reasoning/ Normal Subjective
now to solve this what I do is I send the original pdf again to the LLM and the output looks like this:

```json
{
  "question-1": {
    "question_type": "MCQ",
    "marks": "[1] mark"
  },
  …… [truncated since one example was enough]
  "question-20": {
    "question_type": "Assertion Reasoning",
    "marks": "[1] mark"
  },
  "question-21": {
    "question_type": "Normal Subjective",
    "marks": "[2] marks"
  },   …… [truncated since one example was enough]

  "question-24": {
    "question_type": "Internal Choice Subjective",
    "marks": ["This question has [2] marks", "This question has [2] marks"]
  },
  "question-25": {
    "question_type": "Internal Choice Subjective",
    "marks": ["This question has [3] marks", "This question has [3] marks"]
  },
  "question-38": {
    "question_type": "Case Study",
    "marks": "Part (i): 1 mark, Part (ii): 1 mark, Part (iii): 2 marks OR Part (iii): 2 marks"
  }
```
````

Here we have the main quetion identifer, the marks for each question, and also the question type
now what that we have the question type and marks as well for each question we can map to out final strucutre in a beautiful card
here you will see that we have an array for marks of quesitons of internal choice generally choice-1 and choice-2 have same marks but still it's done so that if there are expetions we can keep track of that also. because there may be a case where question have subparts like this 31. (a) (i) What is the source of force acting on a current-carrying conductor placed in a magnetic field ? Obtain the expression for force acting between two long straight parallel conductors carrying steady currents and hence define ‘ampere'.
(ii) A point charge q is moving with velocity $\vec{v}$ in a uniform magnetic field $\vec{B}$. Find the work done by the magnetic force on the charge.
(iii) Explain the necessary conditions in which the trajectory of a charged particle is helical in a uniform magnetic field.
[%OR%]
(b) (i) A current carrying loop can be considered as a magnetic dipole placed along its axis. Explain.
(ii) Obtain the relation for magnetic dipole moment $\vec{M}$ of current carrying coil. Give the direction of $\vec{M}$.
(iii) A current carrying coil is placed in an external uniform magnetic field. The coil is free to turn in the magnetic field. What is the net force acting on the coil ? Obtain the orientation of the coil in stable equilibrium. Show that in this orientation the flux of the total field (field produced by the loop + external field) through the coil is maximum.
[####]

in these cases we will need the array. since since each question in the choice has diffrernt subparts and subpaparts may have a differnt marks associated with them
"question-31": {
"question_type": "Internal Choice Subjective",
"marks": ["Part (a): (i) 5 marks, (ii) 5 marks, (iii) 5 marks", "Part (b): (i) 5 marks, (ii) 5 marks, (iii) 5 marks"]
},
question number
question text
diagram associated to the question
marks associated to the question
