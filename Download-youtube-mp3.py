import os
import subprocess
import shlex
from pytubefix import YouTube

def telecharger_youtube_en_mp3(url, chemin_sortie="."):
    try:
        print(f"Connexion à l'URL : {url}")
        yt = YouTube(url)
        flux_audio = yt.streams.filter(only_audio=True).first()
        if not flux_audio:
            print(f"❌ Aucun flux audio trouvé pour '{yt.title}'.")
            return

        print(f"Téléchargement de '{yt.title}'...")
        fichier_telecharge = flux_audio.download(output_path=chemin_sortie)

        # Nom du fichier MP3
        base, _ = os.path.splitext(fichier_telecharge)
        fichier_mp3 = base + ".mp3"

        # Utilisation de shlex.quote pour gérer les espaces et caractères spéciaux
        input_file = shlex.quote(fichier_telecharge)
        output_file = shlex.quote(fichier_mp3)

        print("Conversion en MP3...")
        subprocess.run(
    f'ffmpeg -y -i "{fichier_telecharge}" -vn -ab 192k -ar 44100 -f mp3 "{fichier_mp3}"',
    shell=True,
    check=True
)


        # Supprimer le fichier source
        os.remove(fichier_telecharge)
        print(f"✅ Fichier '{os.path.basename(fichier_mp3)}' enregistré avec succès !")

    except Exception as e:
        print(f"❌ Erreur avec l'URL {url} : {e}")


if __name__ == "__main__":
    # Dossier où enregistrer les MP3
    dossier_de_sortie = "C:/Users/Nico/Music/wonka"

    # Liste des vidéos YouTube à télécharger
    liste_urls = [
        "https://youtu.be/gi5_PpLwMqU",
        "https://youtu.be/JXw0FIOftWI",
        "https://youtu.be/N32_wTRm-QU",
        "https://youtu.be/OuXaGE2GWaA",
        "https://youtu.be/6pCwQnJT-so",
        "https://youtu.be/d4EJMmpiBZM",
        "https://youtu.be/RnvEAq_Ue04",
        "https://youtu.be/31_Y9fijPok",
        "https://youtu.be/pKrADHw4utk",
        "https://youtu.be/eptCoIz36F4",
        "https://youtu.be/jcIRqvjzQSM",
        "https://youtu.be/UrSjXlCj00o"
    ]

    print(f"🚀 Lancement du téléchargement pour {len(liste_urls)} vidéo(s).")
    print(f"📁 Fichiers enregistrés dans : {os.path.abspath(dossier_de_sortie)}")

    for i, url in enumerate(liste_urls, start=1):
        print("\n" + "="*50)
        print(f"Traitement de la vidéo {i}/{len(liste_urls)}")
        telecharger_youtube_en_mp3(url, chemin_sortie=dossier_de_sortie)

    print("\n" + "="*50)
    print("🎉 Tous les téléchargements sont terminés !")
