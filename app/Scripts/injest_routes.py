import pdfplumber

text = ""
with pdfplumber.open(r"C:\Users\amazo\Desktop\Projects\Network_monitor\Task-Automation-API\bus-tracker-api\app\Scripts\metro10.pdf") as routes:
    for page in routes.pages:
        text += page.extract_text() + "\n"
        print(text)
    
    

    