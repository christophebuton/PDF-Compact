#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Compact — petite interface graphique (Tkinter) pour compresser un PDF
avec Ghostscript.

Principe général :
  1. L'utilisateur choisit un PDF source, un fichier de sortie et une qualité.
  2. Le programme lance Ghostscript ("gs") dans un processus séparé.
  3. Un thread de travail lit la sortie de Ghostscript ligne par ligne pour
     détecter la page en cours de traitement et faire avancer la barre de
     progression, sans bloquer l'interface.

Prérequis : Ghostscript installé et accessible dans le PATH (commande "gs").
"""

# --- Imports -----------------------------------------------------------------
import tkinter as tk                                  # Bibliothèque graphique standard
from tkinter import filedialog, messagebox, ttk       # Boîtes de dialogue, messages, widgets "thèmes"
import subprocess                                     # Pour lancer Ghostscript comme programme externe
import os                                             # Chemins et vérification d'existence de fichiers
import threading                                      # Pour ne pas figer la fenêtre pendant la compression
import re                                             # Expressions régulières (lecture de la sortie de gs)


# =============================================================================
# Fonctions utilitaires
# =============================================================================

def get_pdf_page_count(filepath):
    """Récupère le nombre total de pages via Ghostscript.

    On exécute un petit programme PostScript passé avec l'option -c :
      - "(fichier) (r) file"  ouvre le PDF en lecture ;
      - "runpdfbegin"         initialise l'interpréteur PDF sur ce fichier ;
      - "pdfpagecount ="      affiche le nombre de pages sur la sortie standard ;
      - "quit"                termine Ghostscript.
    Retourne 0 si quelque chose se passe mal (la barre sera alors indéterminée).
    """
    cmd = [
        "gs", "-q", "-dNODISPLAY", "-c",   # -q : silencieux, -dNODISPLAY : pas de fenêtre graphique
        f"({filepath}) (r) file runpdfbegin pdfpagecount = quit"
    ]
    try:
        # capture_output + text : on récupère la sortie sous forme de chaîne
        # check=True : lève une exception si gs renvoie un code d'erreur
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())   # La sortie est juste un nombre
    except:
        # Ghostscript absent, PDF illisible, sortie inattendue... : on renvoie 0
        return 0


def run_compression():
    """Appelée au clic sur « Lancer la compression ».

    Vérifie les champs, désactive le bouton, puis lance le travail réel
    dans un thread à part pour garder l'interface réactive.
    """
    # Lecture des valeurs saisies dans l'interface
    input_file = entry_input.get()
    output_file = entry_output.get()
    quality = var_quality.get()   # "/screen", "/ebook" ou "/printer"

    # Validation minimale : le fichier source doit exister
    if not input_file or not os.path.exists(input_file):
        messagebox.showwarning("Erreur", "Fichier source invalide.")
        return

    # Empêche un double clic pendant la compression et informe l'utilisateur
    btn_run.config(state="disabled")
    label_status.config(text="Compression en cours...")

    def execute():
        """Travail effectué dans le thread secondaire (ne touche pas directement à l'UI)."""
        total_pages = get_pdf_page_count(input_file)

        # Si on connaît le nombre de pages, on configure la barre (0 → total).
        # root.after(0, ...) planifie l'action dans le thread principal :
        # Tkinter n'est pas thread-safe, on ne modifie donc l'UI que de là.
        if total_pages > 0:
            root.after(0, lambda: progress_bar.config(mode="determinate", maximum=total_pages, value=0))

        # Construction de la commande Ghostscript :
        cmd = [
            "gs", "-sDEVICE=pdfwrite",          # Périphérique de sortie : écriture d'un PDF
            "-dCompatibilityLevel=1.4",         # Version PDF 1.4 (large compatibilité)
            f"-dPDFSETTINGS={quality}",         # Préréglage de qualité/compression
            "-dNOPAUSE", "-dBATCH",             # Pas d'interaction, quitter à la fin
            f"-sOutputFile={output_file}",      # Fichier de sortie
            input_file                          # Fichier source
        ]

        try:
            # Popen lance gs sans attendre, ce qui permet de lire sa sortie en direct.
            # stderr redirigé vers stdout : on lit tout dans un seul flux.
            # bufsize=1 : lecture ligne par ligne (mode texte).
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            # Ghostscript écrit « Page 1 », « Page 2 », ... pendant le traitement.
            for line in process.stdout:
                match = re.search(r"Page\s+(\d+)", line)   # Cherche « Page » suivi d'un nombre
                if match:
                    p = int(match.group(1))
                    # "val=p" fige la valeur actuelle de p dans la lambda
                    # (sinon la lambda verrait la dernière valeur de p au moment de l'exécution)
                    root.after(0, lambda val=p: update_progress(val, total_pages))

            process.wait()   # Attend la fin effective du processus
            # NB : le code de retour (process.returncode) n'est pas vérifié ;
            # un échec de gs affichera donc quand même « Succès ».
            root.after(0, lambda: finalize("Succès", "Compression terminée !"))
        except Exception as e:
            # Par exemple : "gs" introuvable. On transmet le message à l'UI.
            # "err=e" : en Python 3, la variable de « except ... as e » est supprimée
            # à la sortie du bloc, il faut donc la capturer dans la lambda.
            root.after(0, lambda err=e: finalize("Erreur", str(err)))

    # daemon=True : le thread s'arrête si l'on ferme la fenêtre
    threading.Thread(target=execute, daemon=True).start()


def update_progress(current_page, total_pages):
    """Met à jour la barre et le texte d'état (appelée dans le thread principal)."""
    progress_bar["value"] = current_page
    if total_pages > 0:
        percent = int((current_page / total_pages) * 100)
        label_status.config(text=f"Traitement : Page {current_page} / {total_pages} ({percent}%)")


def finalize(title, message):
    """Remet l'interface dans son état initial et affiche le résultat."""
    progress_bar["value"] = 0                              # Barre remise à zéro
    btn_run.config(state="normal")                         # Bouton de nouveau utilisable
    label_status.config(text="Prêt pour un nouveau fichier.")
    if title == "Succès":
        messagebox.showinfo(title, message)
    else:
        messagebox.showerror(title, message)


def select_input():
    """Ouvre l'explorateur pour choisir le PDF source et propose un nom de sortie."""
    filename = filedialog.askopenfilename(
        initialdir=os.path.expanduser("~"),        # Démarre dans le dossier personnel
        filetypes=[("Fichiers PDF", "*.pdf")]      # N'affiche que les PDF
    )
    if filename:   # Vide si l'utilisateur a annulé
        entry_input.delete(0, tk.END)              # Efface l'ancien contenu du champ
        entry_input.insert(0, filename)            # Insère le nouveau chemin
        # Si aucune sortie n'est encore définie, on propose « <nom>_compressed.pdf »
        # dans le même dossier que la source.
        if not entry_output.get():
            base, ext = os.path.splitext(filename)   # Sépare « chemin/nom » et « .pdf »
            entry_output.insert(0, f"{base}_compressed.pdf")


def select_output():
    """Ouvre la boîte « Enregistrer sous » pour choisir le fichier de sortie."""
    filename = filedialog.asksaveasfilename(
        initialdir=os.path.expanduser("~"),
        defaultextension=".pdf",                   # Ajoute .pdf si l'utilisateur l'oublie
        filetypes=[("Fichiers PDF", "*.pdf")]
    )
    if filename:
        entry_output.delete(0, tk.END)
        entry_output.insert(0, filename)


# =============================================================================
# Construction de l'interface
# =============================================================================
root = tk.Tk()   # Fenêtre principale

# Icône facultative : si le fichier est absent ou illisible, on ignore l'erreur
try:
    root.iconphoto(False, tk.PhotoImage(file='pdf-compact.png'))
except Exception:
    pass

root.title("PDF Compact")
root.geometry("640x480")      # Taille initiale (largeur x hauteur)
root.minsize(440, 460)        # Taille minimale pour que tout reste visible

# Police Linux par défaut (DejaVu Sans 12), appliquée à tous les widgets
font_style = ("DejaVu Sans", 12)
root.option_add("*Font", font_style)

# --- Styles ttk (à définir avant de créer les widgets ttk) ---
style = ttk.Style()
style.configure("Run.TButton",
                foreground="black",
                font=("DejaVu Sans", 12, "bold"))
style.configure("Radio.TRadiobutton",
                font=("DejaVu Sans", 12))

# --- Section Entrée ----------------------------------------------------------
ttk.Label(root, text="Fichier source :", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 0))
frame_in = ttk.Frame(root)                          # Conteneur : champ de saisie + bouton côte à côte
frame_in.pack(fill="x", padx=20, pady=5)
entry_input = ttk.Entry(frame_in)
entry_input.pack(side="left", fill="x", expand=True, padx=(0, 5))   # Le champ prend la place restante
ttk.Button(frame_in, text="Chercher", command=select_input).pack(side="right")

# --- Section Sortie ----------------------------------------------------------
ttk.Label(root, text="Fichier de sortie :", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 0))
frame_out = ttk.Frame(root)
frame_out.pack(fill="x", padx=20, pady=5)
entry_output = ttk.Entry(frame_out)
entry_output.pack(side="left", fill="x", expand=True, padx=(0, 5))
ttk.Button(frame_out, text="Modifier", command=select_output).pack(side="right")

# --- Section Qualité (alignée verticalement) ---------------------------------
ttk.Label(root, text="Qualité de compression :", font=("DejaVu Sans", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
var_quality = tk.StringVar(value="/ebook")          # Valeur par défaut : qualité moyenne
radio_frame = ttk.Frame(root)
radio_frame.pack(anchor="w", padx=40)

# (valeur transmise à Ghostscript, texte affiché)
options = [
    ("/screen", "Écran (Basse résolution - 72 DPI)"),
    ("/ebook", "Ebook (Moyenne résolution - 150 DPI)"),
    ("/printer", "Impression (Haute résolution - 300 DPI)")
]

# Un bouton radio par option, tous liés à la même variable : un seul choix possible
for val, txt in options:
    ttk.Radiobutton(radio_frame, text=txt, variable=var_quality, value=val, style="Radio.TRadiobutton").pack(anchor="w", pady=2)

# --- Barre de progression et statut ------------------------------------------
ttk.Label(root, text="Progression :", font=("DejaVu Sans", 10, "italic")).pack(anchor="w", padx=20, pady=(25, 0))
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(fill="x", padx=20, pady=5)

label_status = tk.Label(root, text="Sélectionner un fichier source", fg="#2c3e50")   # Message d'état, mis à jour pendant le travail
label_status.pack(pady=5)

# Le bouton utilise ce style via l'option style=
btn_run = ttk.Button(root, text="Lancer la compression",
                     style="Run.TButton", command=run_compression)
btn_run.pack(pady=20, ipadx=10, ipady=5)

# Boucle principale : affiche la fenêtre et traite les événements jusqu'à la fermeture
root.mainloop()
