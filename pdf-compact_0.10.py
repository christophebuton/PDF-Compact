#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
import re

def get_pdf_page_count(filepath):
    """Récupère le nombre total de pages via Ghostscript."""
    cmd = [
        "gs", "-q", "-dNODISPLAY", "-c",
        f"({filepath}) (r) file runpdfbegin pdfpagecount = quit"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except:
        return 0

def run_compression():
    input_file = entry_input.get()
    output_file = entry_output.get()
    quality = var_quality.get()

    if not input_file or not os.path.exists(input_file):
        messagebox.showwarning("Erreur", "Fichier source invalide.")
        return

    btn_run.config(state="disabled")
    label_status.config(text="Compression en cours...")
    
    def execute():
        total_pages = get_pdf_page_count(input_file)
        
        if total_pages > 0:
            root.after(0, lambda: progress_bar.config(mode="determinate", maximum=total_pages, value=0))
        
        cmd = [
            "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={quality}", "-dNOPAUSE", "-dBATCH",
            f"-sOutputFile={output_file}", input_file
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            for line in process.stdout:
                match = re.search(r"Page\s+(\d+)", line)
                if match:
                    p = int(match.group(1))
                    root.after(0, lambda val=p: update_progress(val, total_pages))

            process.wait()
            root.after(0, lambda: finalize("Succès", "Compression terminée !"))
        except Exception as e:
            root.after(0, lambda: finalize("Erreur", str(e)))

    threading.Thread(target=execute, daemon=True).start()

def update_progress(current_page, total_pages):
    progress_bar["value"] = current_page
    if total_pages > 0:
        percent = int((current_page / total_pages) * 100)
        label_status.config(text=f"Traitement : Page {current_page} / {total_pages} ({percent}%)")

def finalize(title, message):
    progress_bar["value"] = 0
    btn_run.config(state="normal")
    label_status.config(text="Prêt pour un nouveau fichier.")
    if title == "Succès":
        messagebox.showinfo(title, message)
    else:
        messagebox.showerror(title, message)

def select_input():
    filename = filedialog.askopenfilename(filetypes=[("Fichiers PDF", "*.pdf")])
    if filename:
        entry_input.delete(0, tk.END)
        entry_input.insert(0, filename)
        if not entry_output.get():
            base, ext = os.path.splitext(filename)
            entry_output.insert(0, f"{base}_compressed.pdf")

def select_output():
    filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Fichiers PDF", "*.pdf")])
    if filename:
        entry_output.delete(0, tk.END)
        entry_output.insert(0, filename)

# --- Construction de l'interface ---
root = tk.Tk()
try:
    root.iconphoto(False, tk.PhotoImage(file='pdf-compact.png'))
except Exception:
    pass

root.title("PDF Compact")
root.geometry("600x500")
root.minsize(440, 500)

# Police Linux par défaut (DejaVu Sans 12)
font_style = ("DejaVu Sans", 12)
root.option_add("*Font", font_style)

# Section Entrée
tk.Label(root, text="Fichier source :", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", padx=20, pady=(15,0))
frame_in = tk.Frame(root)
frame_in.pack(fill="x", padx=20, pady=5)
entry_input = tk.Entry(frame_in)
entry_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
tk.Button(frame_in, text="Chercher", command=select_input).pack(side="right")

# Section Sortie
tk.Label(root, text="Fichier de sortie :", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", padx=20, pady=(15,0))
frame_out = tk.Frame(root)
frame_out.pack(fill="x", padx=20, pady=5)
entry_output = tk.Entry(frame_out)
entry_output.pack(side="left", fill="x", expand=True, padx=(0, 5))
tk.Button(frame_out, text="Modifier", command=select_output).pack(side="right")

# Section Qualité (Alignée verticalement)
tk.Label(root, text="Qualité de compression :", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
var_quality = tk.StringVar(value="/ebook")
radio_frame = tk.Frame(root)
radio_frame.pack(anchor="w", padx=40)

options = [
    ("/screen", "Écran (Basse résolution - 72 DPI)"),
    ("/ebook", "Ebook (Moyenne résolution - 150 DPI)"),
    ("/printer", "Impression (Haute résolution - 300 DPI)")
]

for val, txt in options:
    tk.Radiobutton(radio_frame, text=txt, variable=var_quality, value=val).pack(anchor="w", pady=2)

# Barre de progression et Statut
tk.Label(root, text="Progression :", font=("DejaVu Sans", 10, "italic")).pack(anchor="w", padx=20, pady=(25, 0))
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(fill="x", padx=20, pady=5)

label_status = tk.Label(root, text="Prêt", fg="#2c3e50")
label_status.pack(pady=5)

# Bouton de lancement
btn_run = tk.Button(root, text="Lancer la compression", fg="black", 
                    font=("DejaVu Sans", 12, "bold"), command=run_compression)
btn_run.pack(pady=20, ipadx=10, ipady=5)

root.mainloop()
