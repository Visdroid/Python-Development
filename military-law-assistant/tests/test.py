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

# --- PDF URLs and Paths ---
# Military documents
pdf_url_1 = "https://www.gov.za/sites/default/files/gcis_document/201911/military-discipline-bill-b21-2019.pdf"
pdf_url_2 = "https://www.gov.za/sites/default/files/gcis_document/201409/b31-99.pdf"
pdf_url_3 = "https://www.gov.za/sites/default/files/gcis_document/201409/a42-02.pdf"
# Law enforcement documents
pdf_url_4 = "https://www.gov.za/sites/default/files/gcis_document/201409/a51-1977.pdf"  # Criminal Procedure Act

pdf_path_1 = "military-discipline-bill.pdf"
pdf_path_2 = "b31-99.pdf"
pdf_path_3 = "defence-act-42-of-2002.pdf"
pdf_path_4 = "criminal-procedure-act.pdf"  # NEW

# Download all PDFs if not present
pdfs_to_download = [
    (pdf_url_1, pdf_path_1),
    (pdf_url_2, pdf_path_2),
    (pdf_url_3, pdf_path_3),
    (pdf_url_4, pdf_path_4)  # NEW
]

for url, path in pdfs_to_download:
    if not os.path.exists(path):
        response = requests.get(url)
        with open(path, "wb") as f:
            f.write(response.content)

# Extract text from all PDFs
pdf_text = ""
pdf_files = [pdf_path_1, pdf_path_2, pdf_path_3, pdf_path_4]  # Added new PDF

for pdf_file in pdf_files:
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            pdf_text += page.extract_text() + "\n"

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_ai(question):
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an expert on both South African Military Law AND Criminal Procedure. "
                        "Answer questions for military, police, or security personnel. "
                        "For military questions, reference the Military Discipline Bill. "
                        "For law enforcement, use the Criminal Procedure Act. "
                        "Context:\n" + pdf_text[:4000]
                    )
                },
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# --- GUI Setup ---
root = tk.Tk()
root.title("Military & Law Enforcement Assistant")
root.geometry("650x440")
root.configure(bg=BG_COLOR)

frame = tk.Frame(root, padx=18, pady=18, bg=BG_COLOR)
frame.pack(fill=tk.BOTH, expand=True)

label = tk.Label(frame, 
                text="Military & Law Enforcement Assistant", 
                font=TITLE_FONT, 
                fg=ACCENT_COLOR, 
                bg=BG_COLOR)
label.pack(anchor='center', pady=(0, 10))

sub_label = tk.Label(frame, 
                    text="Ask about Military Discipline or Criminal Procedure:", 
                    font=LABEL_FONT, 
                    fg=TEXT_COLOR, 
                    bg=BG_COLOR)
sub_label.pack(anchor='w', pady=(0, 6))

question_entry = tk.Entry(frame, 
                         width=80, 
                         font=FONT, 
                         bg=ENTRY_BG, 
                         fg=TEXT_COLOR, 
                         relief='flat', 
                         highlightthickness=2, 
                         highlightbackground=ACCENT_COLOR)
question_entry.pack(fill=tk.X, pady=5, ipady=6)

ask_button = tk.Button(frame, 
                      text="Ask", 
                      font=LABEL_FONT, 
                      bg=BUTTON_COLOR, 
                      fg=BUTTON_TEXT, 
                      activebackground=ACCENT_COLOR, 
                      activeforeground=BUTTON_TEXT, 
                      relief='flat', 
                      bd=0, 
                      padx=16, 
                      pady=6, 
                      cursor='hand2')
ask_button.pack(pady=8)

answer_label = tk.Label(frame, 
                       text="AI Answer:", 
                       font=LABEL_FONT, 
                       fg=TEXT_COLOR, 
                       bg=BG_COLOR)
answer_label.pack(anchor='w', pady=(12,0))

answer_text = scrolledtext.ScrolledText(frame, 
                                      height=10, 
                                      state='disabled', 
                                      wrap=tk.WORD, 
                                      font=FONT, 
                                      bg=ANSWER_BG, 
                                      fg=TEXT_COLOR, 
                                      relief='flat', 
                                      borderwidth=2, 
                                      highlightthickness=1, 
                                      highlightbackground=ACCENT_COLOR)
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