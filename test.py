import os
import openai
import requests
import pdfplumber
import tkinter as tk
from tkinter import scrolledtext, messagebox

# --- Material-inspired colors ---
BG_COLOR = '#f5f5f5'  # light grey
ACCENT_COLOR = '#1976d2'  # material blue
TEXT_COLOR = '#212121'  # dark grey
BUTTON_COLOR = '#2196f3'  # lighter blue
BUTTON_TEXT = '#fff'
ENTRY_BG = '#fff'
ANSWER_BG = '#e3f2fd'  # very light blue
FONT = ("Segoe UI", 11)
LABEL_FONT = ("Segoe UI Semibold", 12)
TITLE_FONT = ("Segoe UI Bold", 14)

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


client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def ask_ai(question):
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are an expert on the South African Military Discipline Law Bill. Use the following context to answer questions:\n" + pdf_text[:4000]},
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

root = tk.Tk()
root.title("Military Discipline Law Bill Q&A")
root.geometry("650x440")
root.configure(bg=BG_COLOR)

frame = tk.Frame(root, padx=18, pady=18, bg=BG_COLOR)
frame.pack(fill=tk.BOTH, expand=True)

label = tk.Label(frame, text="Military Discipline Law Bill Q&A", font=TITLE_FONT, fg=ACCENT_COLOR, bg=BG_COLOR)
label.pack(anchor='center', pady=(0, 10))

sub_label = tk.Label(frame, text="Ask me anything about the South African Military Discipline Law Bill:", font=LABEL_FONT, fg=TEXT_COLOR, bg=BG_COLOR)
sub_label.pack(anchor='w', pady=(0, 6))

question_entry = tk.Entry(frame, width=80, font=FONT, bg=ENTRY_BG, fg=TEXT_COLOR, relief='flat', highlightthickness=2, highlightbackground=ACCENT_COLOR)
question_entry.pack(fill=tk.X, pady=5, ipady=6)

ask_button = tk.Button(frame, text="Ask", font=LABEL_FONT, bg=BUTTON_COLOR, fg=BUTTON_TEXT, activebackground=ACCENT_COLOR, activeforeground=BUTTON_TEXT, relief='flat', bd=0, padx=16, pady=6, cursor='hand2')
ask_button.pack(pady=8)

answer_label = tk.Label(frame, text="AI Answer:", font=LABEL_FONT, fg=TEXT_COLOR, bg=BG_COLOR)
answer_label.pack(anchor='w', pady=(12,0))

answer_text = scrolledtext.ScrolledText(frame, height=10, state='disabled', wrap=tk.WORD, font=FONT, bg=ANSWER_BG, fg=TEXT_COLOR, relief='flat', borderwidth=2, highlightthickness=1, highlightbackground=ACCENT_COLOR)
answer_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

def on_ask():
    question = question_entry.get()
    if not question.strip():
        messagebox.showwarning("Input Required", "Please enter a question.")
        return
    answer = ask_ai(question)
    answer_text.config(state='normal')
    answer_text.delete(1.0, tk.END)
    answer_text.insert(tk.END, answer)
    answer_text.config(state='disabled')

ask_button.config(command=on_ask)

root.mainloop()