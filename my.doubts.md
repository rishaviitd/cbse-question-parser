Question-1:

The current situation is that for the page extraction and conversion there are two ways first is that I take each page as a .pdf and send each single page pdf to the gemini LLM or first I convert the pdf to image and then send every page to the LLM what will be the better approach cosider production grade settings. I will have frontend where the user will upload the pdf and we can run the pdf to image conversion code another way is FAST API backend where I can convert the pdf to image but this will make the server heavy. Or another way is just each page as a single PDF

Explanation:

Send Each page as .pdf because the model can easly crawl in the pdf since they are not flatened. Also it will be less server intensive.
