#!/usr/bin/env python3
# Rapport-Diag-Ultimate-V11.py
# Version 11 : Compatible PC Fixe (Gère proprement l'absence de batterie) + Tout le reste.

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


# ---------- 2. EXTRACTION MATÉRIEL & DATE ----------

def extract_system_info(text):
    info = {"Model": "Inconnu", "Serial": "Inconnu", "FinalCode": "N/A", "Bios": "", "Date": "Non daté"}
    patterns = {
        "Model": r"MACHINE_MODEL:\s*(.*)",
        "Serial": r"SERIAL_NUMBER:\s*(.*)",
        "FinalCode": r"FINAL_RESULT_CODE\s*(.*)",
        "Bios": r"BIOS_VERSION:\s*(.*)"
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m: info[key] = m.group(1).strip()

    m_date = re.search(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})UTC", text)
    if m_date:
        y, m, d, H, M, S = m_date.groups()
        info["Date"] = f"{d}/{m}/{y} à {H}:{M}:{S}"

    return info

def extract_cpu(text):
    cpu = {"Model": "", "Cores": "", "Threads": "", "MaxSpeed": "", "TempDisplay": "Non dispo", "TempVal": 0}
    patterns = {
        "Model": r"CPU[_\s]*MODEL:\s*(.*)",
        "Cores": r"CPU[_\s]*CORES:\s*(\d+)",
        "Threads": r"CPU[_\s]*THREADS:\s*(\d+)",
        "MaxSpeed": r"CPU[_\s]*MAX[_\s]*SPEED:\s*([0-9\.]+\s*GHz)"
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m: cpu[key] = m.group(1).strip()

    m_temp = re.search(r"CPU_TEMPERATURE:\s*(\d+)\s*[CF]", text, re.IGNORECASE)
    if m_temp:
        try:
            val = int(m_temp.group(1))
            cpu['TempVal'] = val
            cpu['TempDisplay'] = f"{val} °C"
        except ValueError:
            pass
    return cpu

def extract_ram_detail(text):
    ram = {"Total": "Inconnu", "Sticks": []}
    m_total = re.search(r"TOTAL_PHYSICAL_MEMORY:\s*(\d+\s*MB)", text)
    if m_total:
        ram["Total"] = m_total.group(1)

    section_match = re.search(r"MEMORY QUICK DIAGNOSTIC.*?(?=START TESTS)", text, re.DOTALL)
    if section_match:
        section_text = section_match.group(0)
        blocks = section_text.split("ORIGIN: SMBIOS")[1:]
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

def extract_storage(text):
    storage = {
        "Type": "", "Size": "", "Hours": "", "Model": "", 
        "PercentUsed": "", "PowerCycles": ""
    }
    
    section_match = re.search(r"STORAGE\s+(?:QUICK|EXTENDED)\s+DIAGNOSTIC.*?(?=START TESTS)", text, re.DOTALL | re.IGNORECASE)
    target_text = section_match.group(0) if section_match else text 

    patterns = {
        "Type": r"DEVICE[_\s]*TYPE:\s*(.*)",
        "Size": r"INFORMATION[_\s]*SIZE:\s*(.*)",
        "Model": r"MODEL[_\s]*NUMBER:\s*(.*)",
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

def extract_battery(text):
    batt = {"Health": "N/A", "Cycles": "N/A", "Design": 0, "Full": 0, "Found": False}
    
    section_match = re.search(r"BATTERY (?:QUICK|EXTENDED) DIAGNOSTIC.*?(?=START TESTS)", text, re.DOTALL)
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
            except:
                pass
    return batt


# ---------- 3. ANALYSE SANTÉ ----------
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
            current_diag = m_start.group(1).strip()
            diagnostics.append({"name": current_diag, "status": "SUCCESS"})

        if current_diag:
            if m := rx_fail.search(line):
                failures.append(f"{m.group(1)} (Module: {current_diag})")
                if diagnostics: diagnostics[-1]["status"] = "FAILED"
            if m := rx_error.search(line):
                failures.append(f"Erreur {m.group(1)} (Module: {current_diag})")
                if diagnostics: diagnostics[-1]["status"] = "FAILED"
                
    return diagnostics, failures


# ---------- 4. FORMATAGE RAPPORT ----------
def build_full_report(sys_info, cpu, ram, storage, battery, diagnostics, failures):
    lines = []
    lines.append("="*60)
    lines.append(f" RAPPORT DIAGNOSTIC : {sys_info.get('Model')}")
    lines.append("="*60)
    lines.append(f"Date du test    : {sys_info.get('Date')}")
    lines.append(f"Numéro de Série : {sys_info.get('Serial')}")
    lines.append(f"Code Résultat   : {sys_info.get('FinalCode')}")
    lines.append(f"Version BIOS    : {sys_info.get('Bios')}")
    lines.append("")

    # --- MATÉRIEL ---
    lines.append("-" * 25 + " MATÉRIEL " + "-" * 25)
    
    # CPU
    temp_val = cpu.get('TempVal', 0)
    temp_str = cpu.get('TempDisplay', 'N/A')
    SEUIL_CHAUD = 85 
    if temp_val > SEUIL_CHAUD:
        temp_line = f"{temp_str}  ⚠️ SURCHAUFFE (> {SEUIL_CHAUD}°C) !"
    elif temp_val > 0:
        temp_line = f"{temp_str}  (Normal) ✅"
    else:
        temp_line = "Non disponible"

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
            lines.append(f"  - Slot {i+1:<9} : {stick['Size']} - {stick['Type']} - {stick['Manu']} - {stick['Part']} - {stick['Speed']}")
    else:
        lines.append("  - Détail       : Non détecté")
    lines.append("")

    # STOCKAGE
    lines.append("[HDD/SSD] Stockage :")
    lines.append(f"  - Modèle       : {storage.get('Model','')}")
    lines.append(f"  - Type         : {storage.get('Type','')}")
    lines.append(f"  - Capacité     : {storage.get('Size','')}")
    lines.append(f"  - Heures (POH) : {storage.get('Hours','?')} h")
    lines.append(f"  - Cycles       : {storage.get('PowerCycles','')}")
    lines.append("")

    # --- RÉSULTATS TESTS & USURE ---
    lines.append("-" * 25 + " RÉSULTATS & SANTÉ " + "-" * 25)
    
    # 1. Verdict Global
    if failures:
        lines.append("⚠️  VERDICT : ÉCHECS DÉTECTÉS")
        for fail in failures:
            lines.append(f"  [❌] {fail}")
    else:
        lines.append("✅  VERDICT : TOUS LES TESTS ONT RÉUSSI")
    lines.append("")

    # 2. Indicateurs d'Usure
    lines.append("📊  ÉTAT DE SANTÉ / USURE :")
    
    # LOGIQUE AFFICHAGE BATTERIE INTELLIGENTE
    if battery.get("Found"):
        batt_health = battery.get("Health", "N/A")
        batt_cycles = battery.get("Cycles", "N/A")
        lines.append(f"  - Batterie     : Santé {batt_health} ({batt_cycles} cycles)")
    else:
        lines.append(f"  - Batterie     : Non détectée / PC Fixe")
    
    # Stockage
    hours_str = storage.get('Hours','0')
    cycles_str = storage.get('PowerCycles','0')
    percent_used = storage.get('PercentUsed', '?')
    
    try:
        h = int(hours_str)
        c = int(cycles_str)
        if c > 0:
            ratio = h / c
            if ratio < 1.0:
                status = "⚠️ Instable / Haché"
            elif ratio < 10.0:
                status = "✅ Standard"
            else:
                status = "⚡ Intensif"
            lines.append(f"  - Disque       : Usure {percent_used}% (Profil : {ratio:.1f} h/sess -> {status})")
        else:
            lines.append(f"  - Disque       : Usure {percent_used}%")
    except:
        lines.append(f"  - Disque       : Usure {percent_used}%")

    lines.append("")
    
    # 3. Liste Modules
    lines.append("Détail des modules exécutés :")
    for diag in diagnostics:
        icon = "✅" if diag["status"] == "SUCCESS" else "❌"
        lines.append(f"  [{icon}] {diag['name']}")
        
    return "\n".join(lines)


# ---------- 5. UI TKINTER ----------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Rapport Diag Ultimate V11 (Universelle)")
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
        self.text.insert(tk.END, "Analyse...")
        self.root.update()

        try:
            txt = read_and_clean_log(path)
            
            info = extract_system_info(txt)
            cpu = extract_cpu(txt)
            ram = extract_ram_detail(txt)
            hdd = extract_storage(txt)
            batt = extract_battery(txt)
            diags, fails = extract_test_results(txt)

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
                messagebox.showinfo("Succès", "Machine saine (Aucune alerte critique).")

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
