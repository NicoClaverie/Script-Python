# Modules et outils pour le script YouTube → MP3

Ce script télécharge l'audio de vidéos YouTube et les convertit en MP3 sous Windows.

---

## 1️⃣ Modules Python à installer

| Module      | Usage dans le script                                     | Installation |
|------------|---------------------------------------------------------|--------------|
| `pytubefix` | Télécharger les vidéos YouTube sans erreur HTTP 400     | `pip install pytubefix` |
| `subprocess` | Exécuter ffmpeg pour convertir l’audio en MP3         | Inclus dans Python standard |
| `os`        | Gestion des chemins, suppression de fichiers          | Inclus dans Python standard |
| `shlex`     | (Optionnel) sécuriser les chemins pour shell          | Inclus dans Python standard |
| `tempfile`  | (Optionnel) gérer les fichiers temporaires           | Inclus dans Python standard |

---

## 2️⃣ Logiciel externe

| Logiciel   | Usage                                      | Installation | Commande Winget |
|-----------|-------------------------------------------|--------------|
| `ffmpeg`  | Convertir l’audio en MP3                  | Télécharger depuis [ffmpeg.org](https://ffmpeg.org/download.html) et ajouter le dossier `bin` au PATH Windows |winget install "FFmpeg (Essentials Build)"|

---

## 3️⃣ Notes importantes

- `pytubefix` remplace `pytube` pour éviter le **HTTP Error 400**.  
- Les modules Python standard (`os`, `subprocess`, `shlex`, `tempfile`) ne nécessitent pas d’installation.  
- `ffmpeg` doit être **accessible depuis le PATH Windows** pour que le script fonctionne correctement.  

---

## 4️⃣ Vérification

Après installation, vérifie que tout fonctionne :

```powershell
# Vérifier Python et pip
python --version
pip --version

# Vérifier ffmpeg
ffmpeg -version
