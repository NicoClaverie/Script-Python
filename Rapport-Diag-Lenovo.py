#!/usr/bin/env python3
# Rapport-Diag-Ultimate-V18.py
# Version 18 : Correction CRITIQUE de l'extraction Stockage "Legacy".
# Force la détection du bloc STORAGE immédiat pour éviter de lire tout le fichier (et de confondre avec la RAM).

import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# ---------- 1. LECTURE ROBUSTE ----------
def read_and_clean_log(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception as e:
        raise IOError(f"Impossible d'ouvrir le fichier : {e}")

    cleaned = data.replace(b"\x00", b"")
    for b in [b"\x03", b"\x18", b"\x0b", b"\x0c", b"\x1a"]:
        cleaned = cleaned.replace(b, b"")

    return cleaned.decode("latin-1", errors="ignore")


# ---------- 2. DÉTECTION DE VERSION ----------

def get_diag_version(text):
    m = re.search(r"APPLICATION_VERSION:\s*(?:Version|UEFI)?\s*(\d+)\.", text, re.IGNORECASE)
    if m:
        try: return int(m.group(1))
        except: return 4
    return 4


# ---------- 3. EXTRACTION COMMUNES ----------

def extract_common_info(text):
    info = {"Model": "Inconnu", "Serial": "Inconnu", "FinalCode": "N/A", "Bios": "", "Date": "Non daté", "AppVer": "?"}
    patterns = {
        "Model": r"^MACHINE_MODEL:\s*(.*)",
        "Serial": r"^SERIAL_NUMBER:\s*(.*)",
        "FinalCode": r"FINAL_RESULT_CODE\s*(.*)",
        "Bios": r"^BIOS_VERSION:\s*(.*)",
        "AppVer": r"^APPLICATION_VERSION:\s*(.*)"
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.MULTILINE)
        if m: info[key] = m.group(1).strip()

    m_date = re.search(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})UTC", text)
    if m_date:
        y, m, d, H, M, S = m_date.groups()
        info["Date"] = f"{d}/{m}/{y} à {H}:{M}:{S}"
    return info

def extract_cpu(text):
    cpu = {"Model": "", "Cores": "", "Threads": "", "MaxSpeed": "", "TempDisplay": "Non dispo", "TempVal": 0}
    
    # Isolation section CPU
    section = re.search(r"\+\+\+.*?CPU.*?(?=STOP TESTS)", text, re.DOTALL)
    target_text = section.group(0) if section else text

    patterns = {
        "Model": r"CPU[_\s]*MODEL:\s*(.*)",
        "Cores": r"CPU[_\s]*CORES:\s*(\d+)",
        "Threads": r"CPU[_\s]*THREADS:\s*(\d+)",
        "MaxSpeed": r"CPU[_\s]*MAX[_\s]*SPEED:\s*([0-9\.]+\s*GHz)"
    }
    for key, pat in patterns.items():
        m = re.search(pat, target_text, re.IGNORECASE)
        if m: cpu[key] = m.group(1).strip()

    m_temp = re.search(r"CPU_TEMPERATURE:\s*(\d+)\s*[CF]", text, re.IGNORECASE)
    if m_temp:
        val = int(m_temp.group(1))
        cpu['TempVal'] = val
        cpu['TempDisplay'] = f"{val} °C"
    return cpu


# ---------- 4. MOTEUR V4 (MODERNE) ----------

def extract_ram_modern(text):
    ram = {"Total": "Inconnu", "Sticks": []}
    m_total = re.search(r"TOTAL_PHYSICAL_MEMORY:\s*(\d+\s*MB)", text)
    if m_total: ram["Total"] = m_total.group(1)

    section_match = re.search(r"MEMORY QUICK DIAGNOSTIC.*?(?=START TESTS)", text, re.DOTALL)
    if section_match:
        blocks = section_match.group(0).split("ORIGIN: SMBIOS")[1:]
        for block in blocks:
            stick = {}
            def get(pat, txt):
                m = re.search(pat, txt)
                return m.group(1).strip() if m else "?"
            stick['Size'] = get(r"SIZE:\s*(.*)", block)
            stick['Type'] = get(r"TYPE:\s*(.*)", block)
            stick['Manu'] = get(r"MANUFACTURER:\s*(.*)", block)
            stick['Part'] = get(r"PART_NUMBER:\s*(.*)", block)
            speed = get(r"MEMORY_CURRENT_SPEED:\s*(.*)", block)
            if speed == "?": speed = get(r"MEMORY_SPEED:\s*(.*)", block)
            stick['Speed'] = speed
            if stick['Size'] != "?": ram["Sticks"].append(stick)
    return ram

def extract_storage_modern(text):
    storage = {"Type": "", "Size": "", "Hours": "N/A", "Model": "", "PercentUsed": "N/A", "PowerCycles": "N/A"}
    
    match = re.search(r"STORAGE\s+(?:QUICK|EXTENDED)\s+DIAGNOSTIC.*?(?=START TESTS)", text, re.DOTALL | re.IGNORECASE)
    if not match: return storage
    
    target_text = match.group(0)
    patterns = {
        "Type": r"DEVICE_TYPE:\s*(.*)",
        "Size": r"INFORMATION_SIZE:\s*(.*)",
        "Model": r"MODEL_NUMBER:\s*(.*)",
        "PowerCycles": r"Power\s*Cycles\s+(\d+)",
        "PercentUsed": r"Percentage\s*Used\s+(\d+)"
    }
    for key, pat in patterns.items():
        m = re.search(pat, target_text, re.IGNORECASE)
        if m: storage[key] = m.group(1).strip()

    m_hours = re.search(r"Power\s*On\s*Hours\s+(\d+)", target_text, re.IGNORECASE)
    if not m_hours:
         m_hours = re.search(r"^\s*\d+\s+Power\s+On\s+Hours\s+(\d+)", target_text, re.IGNORECASE | re.MULTILINE)
    if m_hours: storage["Hours"] = m_hours.group(1)
    return storage


# ---------- 5. MOTEUR V2 (LEGACY - FIXÉ) ----------

def extract_ram_legacy(text):
    ram = {"Total": "Inconnu", "Sticks": []}
    m_total = re.search(r"PHYSICAL_MEMORY:\s*([\d\.]+\s*[GM]B)", text)
    if m_total: ram["Total"] = m_total.group(1)

    section_match = re.search(r"\+\+\+.*?MEMORY.*?(?=STOP TESTS)", text, re.DOTALL)
    if section_match:
        blocks = section_match.group(0).split("RESOURCE BANK")[1:]
        for block in blocks:
            if "INDEX:" not in block: continue
            stick = {}
            def get(pat, txt):
                m = re.search(pat, txt, re.MULTILINE)
                return m.group(1).strip() if m else "?"
            stick['Size'] = get(r"^SIZE:\s*(.*)", block)
            stick['Type'] = "DDR3/Unknown"
            stick['Manu'] = get(r"^MANUFACTURER:\s*(.*)", block)
            stick['Part'] = get(r"^PART_NUMBER:\s*(.*)", block)
            stick['Speed'] = get(r"^SPEED:\s*(.*)", block)
            if stick['Size'] != "?": ram["Sticks"].append(stick)
    return ram

def extract_storage_legacy(text):
    """
    Correction V18 : Regex STRICTE pour le timestamp STORAGE.
    On ne permet plus de '.*?' entre la date et le mot STORAGE.
    """
    storage = {"Type": "", "Size": "", "Hours": "N/A", "Model": "", "PercentUsed": "N/A", "PowerCycles": "N/A"}
    
    # Regex V18 : Le mot STORAGE doit suivre IMMÉDIATEMENT l'heure UTC (ex: +++ 2025...UTC STORAGE)
    # Cela empêche de matcher le début du fichier et de tout avaler jusqu'à la fin.
    match = re.search(r"(\+\+\+\s+\d+T\d+UTC\s+STORAGE.*?)STOP TESTS", text, re.DOTALL | re.IGNORECASE)
    
    if not match: return storage
    
    target_text = match.group(1)
    
    # On utilise ^ pour matcher le début de ligne DANS le bloc ciblé
    patterns = {
        "Type": r"^TYPE:\s*(.*)",
        "Size": r"^SIZE:\s*(.*)",
        "Model": r"^MODEL:\s*(.*)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, target_text, re.MULTILINE | re.IGNORECASE)
        if m: storage[key] = m.group(1).strip()
    
    storage["Hours"] = "N/A (Vieux Log)"
    return storage


# ---------- 6. FONCTIONS COMMUNES ----------

def extract_battery(text):
    batt = {"Health": "N/A", "Cycles": "N/A", "Design": 0, "Full": 0, "Found": False}
    section_match = re.search(r"BATTERY (?:QUICK|EXTENDED)?\s*DIAGNOSTIC.*?(?=START TESTS)", text, re.DOTALL)
    if section_match:
        batt["Found"] = True
        block = section_match.group(0)
        
        m_cyc = re.search(r"CYCLE_COUNT:\s*(\d+)", block)
        if m_cyc: batt["Cycles"] = m_cyc.group(1)

        m_des = re.search(r"DESIGN_CAPACITY:\s*(\d+)", block)
        m_full = re.search(r"FULL_CHARGE_CAPACITY:\s*(\d+)", block)
        
        if m_des and m_full:
            try:
                d = float(m_des.group(1))
                f = float(m_full.group(1))
                batt["Design"] = d
                batt["Full"] = f
                if d > 0:
                    pct = (f / d) * 100
                    batt["Health"] = f"{pct:.1f}%"
            except: pass
    return batt

def extract_test_results(text):
    lines = text.splitlines()
    diagnostics = []
    failures = []
    
    rx_diag_start = re.compile(r"^\+\+\+\s+\d+T\d+UTC\s+(.*?)(\s+\d{10,}|$)")
    rx_fail = re.compile(r"STOP\s+(.*)\s+FAILED")
    rx_error = re.compile(r"^ERROR\s+(.*)")
    current_diag = None
    
    for line in lines:
        line = line.strip()
        m_start = rx_diag_start.search(line)
        if m_start:
            raw_name = m_start.group(1).strip()
            # On nettoie l'ID à la fin
            current_diag = re.sub(r"\s+\d+$", "", raw_name)
            diagnostics.append({"name": current_diag, "status": "SUCCESS"})

        if current_diag:
            if m := rx_fail.search(line):
                failures.append(f"{m.group(1)} (Module: {current_diag})")
                if diagnostics: diagnostics[-1]["status"] = "FAILED"
            if m := rx_error.search(line):
                failures.append(f"Erreur {m.group(1)} (Module: {current_diag})")
                if diagnostics: diagnostics[-1]["status"] = "FAILED"
                
    return diagnostics, failures


# ---------- 7. FORMATAGE RAPPORT ----------
def build_full_report(sys_info, cpu, ram, storage, battery, diagnostics, failures):
    lines = []
    lines.append("="*60)
    lines.append(f" RAPPORT DIAGNOSTIC : {sys_info.get('Model')}")
    lines.append("="*60)
    lines.append(f"Version App     : {sys_info.get('AppVer')}")
    lines.append(f"Date du test    : {sys_info.get('Date')}")
    lines.append(f"Numéro de Série : {sys_info.get('Serial')}")
    lines.append(f"Code Résultat   : {sys_info.get('FinalCode')}")
    lines.append("")

    lines.append("-" * 25 + " MATÉRIEL " + "-" * 25)
    
    # CPU
    temp_val = cpu.get('TempVal', 0)
    temp_str = cpu.get('TempDisplay', 'N/A')
    SEUIL_CHAUD = 85 
    if temp_val > SEUIL_CHAUD: temp_line = f"{temp_str}  ⚠️ SURCHAUFFE (> {SEUIL_CHAUD}°C) !"
    elif temp_val > 0: temp_line = f"{temp_str}  (Normal) ✅"
    else: temp_line = "Non disponible (Sonde absente ou vieux log)"

    lines.append("[CPU] Processeur :")
    lines.append(f"  - Modèle       : {cpu.get('Model','')}")
    lines.append(f"  - Vitesse Max  : {cpu.get('MaxSpeed','')}")
    lines.append(f"  - Coeurs       : {cpu.get('Cores','?')} Coeurs / {cpu.get('Threads','?')} Threads")
    lines.append(f"  - Température  : {temp_line}") 
    lines.append("")
    
    # RAM
    lines.append("[RAM] Mémoire Vive :")
    lines.append(f"  - Total        : {ram.get('Total', 'Inconnu')}")
    if ram.get("Sticks"):
        for i, stick in enumerate(ram["Sticks"]):
            type_str = stick.get('Type', '?')
            manu_str = stick.get('Manu', '?')
            if "0000" in manu_str: manu_str = "Générique/Inconnu"
            lines.append(f"  - Slot {i+1:<9} : {stick['Size']} - {type_str} - {manu_str} - {stick['Part']} - {stick['Speed']}")
    else:
        lines.append("  - Détail       : Non détecté")
    lines.append("")

    # STOCKAGE
    lines.append("[HDD/SSD] Stockage :")
    lines.append(f"  - Modèle       : {storage.get('Model','')}")
    lines.append(f"  - Type         : {storage.get('Type','')}")
    lines.append(f"  - Capacité     : {storage.get('Size','')}")
    lines.append(f"  - Heures (POH) : {storage.get('Hours','N/A')}")
    lines.append(f"  - Cycles       : {storage.get('PowerCycles','N/A')}")
    lines.append("")

    lines.append("-" * 25 + " RÉSULTATS & SANTÉ " + "-" * 25)
    
    if failures:
        lines.append("⚠️  VERDICT : ÉCHECS DÉTECTÉS")
        for fail in failures:
            lines.append(f"  [❌] {fail}")
    else:
        lines.append("✅  VERDICT : TOUS LES TESTS ONT RÉUSSI")
    lines.append("")

    lines.append("📊  ÉTAT DE SANTÉ / USURE :")
    
    # Batterie
    if battery.get("Found"):
        batt_health = battery.get("Health", "N/A")
        batt_cycles = battery.get("Cycles", "N/A")
        lines.append(f"  - Batterie     : Santé {batt_health} ({batt_cycles} cycles)")
    else:
        lines.append(f"  - Batterie     : Non détectée / PC Fixe / Vieux Log")
    
    # Stockage (Profil Usage)
    hours_str = storage.get('Hours','N/A')
    cycles_str = storage.get('PowerCycles','N/A')
    percent_used = storage.get('PercentUsed', 'N/A')
    
    if hours_str != "N/A" and cycles_str != "N/A" and "Vieux" not in hours_str:
        try:
            h = int(hours_str)
            c = int(cycles_str)
            if c > 0:
                ratio = h / c
                if ratio < 1.0: status = "⚠️ Instable / Haché"
                elif ratio < 10.0: status = "✅ Standard"
                else: status = "⚡ Intensif"
                lines.append(f"  - Disque       : Usure {percent_used}% (Profil : {ratio:.1f} h/sess -> {status})")
            else:
                lines.append(f"  - Disque       : Usure {percent_used}%")
        except:
            lines.append(f"  - Disque       : Usure {percent_used}%")
    else:
        if "Vieux" in hours_str:
             lines.append(f"  - Disque       : Données SMART non disponibles (Vieux Log)")
        else:
             lines.append(f"  - Disque       : Données SMART non disponibles")

    lines.append("")
    
    lines.append("Détail des modules exécutés :")
    for diag in diagnostics:
        icon = "✅" if diag["status"] == "SUCCESS" else "❌"
        lines.append(f"  [{icon}] {diag['name']}")
        
    return "\n".join(lines)


# ---------- 8. UI TKINTER ----------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Rapport Diag Ultimate V18 (Fix Legacy)")
        root.geometry("950x750")

        frame = tk.Frame(root)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(frame, text="📂 Ouvrir Log", command=self.open_log, bg="#e1e1e1", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="💾 Sauvegarder", command=self.save_summary).pack(side=tk.LEFT, padx=5)

        self.text = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 10))
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.current_report = ""

    def open_log(self):
        path = filedialog.askopenfilename(filetypes=[("Log", "*.log"), ("Tous", "*.*")])
        if not path: return
        
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, "Lecture et détection de version...\n")
        self.root.update()

        try:
            txt = read_and_clean_log(path)
            
            ver = get_diag_version(txt)
            self.text.insert(tk.END, f"-> Version Détectée : Génération {ver}\n")
            
            info = extract_common_info(txt)
            cpu = extract_cpu(txt)
            batt = extract_battery(txt)
            diags, fails = extract_test_results(txt)

            if ver >= 4:
                ram = extract_ram_modern(txt)
                hdd = extract_storage_modern(txt)
            else:
                ram = extract_ram_legacy(txt)
                hdd = extract_storage_legacy(txt)

            rep = build_full_report(info, cpu, ram, hdd, batt, diags, fails)
            self.current_report = rep
            
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, rep)
            
            alerts = []
            if cpu.get('TempVal', 0) > 85: alerts.append("Surchauffe CPU")
            if fails: alerts.append(f"{len(fails)} Test(s) échoué(s)")
            
            if alerts:
                messagebox.showwarning("Attention", " / ".join(alerts))
            else:
                messagebox.showinfo("Succès", "Analyse Terminée.")

        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def save_summary(self):
        if not self.current_report: return
        p = filedialog.asksaveasfilename(defaultextension=".txt")
        if p:
            with open(p, "w", encoding="utf-8") as f: f.write(self.current_report)
            messagebox.showinfo("Info", "Fichier enregistré.")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
