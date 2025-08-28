# Penser a installer pytube et moviepy grace a `pip install pytube moviepy`

import os
from pytube import YouTube
from moviepy.editor import *

def telecharger_youtube_en_mp3(url, chemin_sortie="."):
    """
    Télécharge l'audio d'une vidéo YouTube et la convertit en MP3.

    :param url: L'URL de la vidéo YouTube.
    :param chemin_sortie: Le dossier où enregistrer le fichier MP3.
    """
    try:
        # --- 1. Téléchargement de la vidéo ---
        print(f"Connexion à l'URL : {url}")
        yt = YouTube(url)
        print(f"Téléchargement de '{yt.title}'...")

        # Sélection du meilleur flux audio disponible
        flux_audio = yt.streams.filter(only_audio=True).first()
        if not flux_audio:
            print(f"❌ Aucun flux audio trouvé pour '{yt.title}'. Passage au suivant.")
            return # On arrête le traitement pour CETTE vidéo

        # Téléchargement du fichier audio (souvent au format .mp4 ou .webm)
        fichier_telecharge = flux_audio.download(output_path=chemin_sortie)
        print("Téléchargement audio terminé.")

        # --- 2. Conversion en MP3 ---
        print("Conversion en MP3...")
        base, ext = os.path.splitext(fichier_telecharge)
        fichier_mp3 = base + '.mp3'

        # Chargement du fichier audio et écriture en MP3
        clip_audio = AudioFileClip(fichier_telecharge)
        clip_audio.write_audiofile(fichier_mp3, logger=None) # logger=None pour un affichage plus propre
        clip_audio.close()

        # --- 3. Nettoyage ---
        os.remove(fichier_telecharge)
        print(f"✅ Fichier '{os.path.basename(fichier_mp3)}' enregistré avec succès !")

    except Exception as e:
        print(f"❌ Une erreur est survenue avec l'URL {url} : {e}")
    # 👇 **INDSCRIVEZ ICI LE CHEMIN DE VOTRE DOSSIER** 👇
    # Assurez-vous que le dossier existe !
    
    # Exemple pour Windows :
    dossier_de_sortie = "C:/Users/claverie/Music" 
    
    # Exemple pour macOS ou Linux :
    # dossier_de_sortie = "/Users/VotreNom/Music"

    # Si vous voulez juste un sous-dossier nommé "MP3" là où se trouve le script :
    # dossier_de_sortie = "MP3"
    
    print(f"🚀 Lancement du téléchargement pour {len(liste_urls)} vidéo(s).")
    print(f"📁 Fichiers enregistrés dans : {os.path.abspath(dossier_de_sortie)}") # Affiche le chemin complet
    
# --- Utilisation du script ---
if __name__ == "__main__":
    # 👇 **MODIFIEZ CETTE LISTE avec vos propres liens YouTube** 👇
    liste_urls = [
        "https://youtu.be/gi5_PpLwMqU?si=3XmE32iyfHPbTmwh",
        "https://youtu.be/JXw0FIOftWI?si=XxBAjQs-_MD9IEOY",
        "https://youtu.be/N32_wTRm-QU?si=b9Y0JqHH6sJiKqoE"
    ]
    
    print(f"🚀 Lancement du téléchargement pour {len(liste_urls)} vidéo(s).")
    
    # On boucle sur chaque URL de la liste
    for i, url in enumerate(liste_urls):
        print("\n" + "="*50)
        print(f"Traitement de la vidéo {i+1}/{len(liste_urls)}")
        telecharger_youtube_en_mp3(url) # On appelle la fonction pour chaque lien

    print("\n" + "="*50)
    print("🎉 Tous les téléchargements sont terminés !")
