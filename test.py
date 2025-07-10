import os
import openai
import requests
import pdfplumber

# Download and extract text from the PDF
pdf_url = "https://www.gov.za/sites/default/files/gcis_document/201911/military-discipline-bill-b21-2019.pdf"
pdf_path = "military-discipline-bill.pdf"

if not os.path.exists(pdf_path):
    response = requests.get(pdf_url)
    with open(pdf_path, "wb") as f:
        f.write(response.content)

with pdfplumber.open(pdf_path) as pdf:
    pdf_text = ""
    for page in pdf.pages:
        pdf_text += page.extract_text() + "\n"

# Set your OpenAI API key directly (for local/testing use only)
client = openai.OpenAI(api_key="OpenAI_API_Key")

question = input("Ask me anything about the South African Military Discipline Law Bill: ")

response = client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {"role": "system", "content": "You are an expert on the South African Military Discipline Law Bill. Use the following context to answer questions:\n" + pdf_text[:4000]},  # Truncate to fit token limits
        {"role": "user", "content": question}
    ]
)

print("AI:", response.choices[0].message.content)

#This code downloads the PDF, extracts its text, and uses the OpenAI API to answer questions about the South African Military Discipline Law Bill. Make sure to replace `"OpenAI_API_Key"` with your actual OpenAI API key. The PDF text is truncated to fit within token limits for the model