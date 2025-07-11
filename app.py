from flask import Flask, render_template, request, jsonify
import os
import openai
import requests
import pdfplumber

app = Flask(__name__)

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

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are an expert on the South African Military Discipline Law Bill. Use the following context to answer questions:\n" + pdf_text[:4000]},
                {"role": "user", "content": question}
            ]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Error: {e}"
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)
