import os
import subprocess
import shlex
from pytubefix import YouTube

def telecharger_youtube_en_mp3(url, chemin_sortie=".", track_number=None, album_name=None):
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

        # Infos métadonnées
        titre = yt.title
        auteur = str("id Software and Mick Gordon")
        #album = album_name if album_name else "YouTube Playlist"
        album = str("OST DOOM 2016")
        piste = str(track_number) if track_number else "1"

        print("Conversion en MP3 avec métadonnées...")
        commande = (
            f'ffmpeg -y -i "{fichier_telecharge}" -vn -ab 192k -ar 44100 -f mp3 '
            f'-metadata title="{titre}" '
            f'-metadata artist="{auteur}" '
            f'-metadata album="{album}" '
            f'-metadata track="{piste}" '
            f'"{fichier_mp3}"'
        )
        subprocess.run(commande, shell=True, check=True)

        # Supprimer le fichier source
        os.remove(fichier_telecharge)
        print(f"✅ Fichier '{os.path.basename(fichier_mp3)}' enregistré avec succès !")

    except Exception as e:
        print(f"❌ Erreur avec l'URL {url} : {e}")


if __name__ == "__main__":
    # Dossier où enregistrer les MP3
    dossier_de_sortie = "J:\Musique de films\DOOM 2016 OST"

    # Liste des vidéos YouTube à télécharger
    liste_urls = [
    "https://youtu.be/7o9W-7JHs_w",
"https://youtu.be/vyA1z2A-lhU",
"https://youtu.be/HPZ5CxfuKqU",
"https://youtu.be/pZB9cxJoLgk",
"https://youtu.be/L27BrUg4lG8",
"https://youtu.be/CjbANqQqxcA",
"https://youtu.be/tsryWtOZ010",
"https://youtu.be/IyKEijqG82g",
"https://youtu.be/TsDAY7YcCys",
"https://youtu.be/VOV2Dh2W8_c",
"https://youtu.be/EHM2OIcG8Ok",
"https://youtu.be/nD5ssUt73LY",
"https://youtu.be/LaQrORUWec0",
"https://youtu.be/xzlz2oUJlAs",
"https://youtu.be/VYHIpx8RVmk",
"https://youtu.be/mvKWGtB6s7Q",
"https://youtu.be/fDs3wd9inQk",
"https://youtu.be/YtxO7eSmYQU",
"https://youtu.be/aFmIS-4GTwo",
"https://youtu.be/A-1DLeuxC0M",
"https://youtu.be/-fVynlsxkeg",
"https://youtu.be/_3VHzhVaIts",
"https://youtu.be/GX47QeNeZjQ",
"https://youtu.be/udCvNyopFRI",
"https://youtu.be/A02t5hx1sHM",
"https://youtu.be/wKSVH5gd3oQ",
"https://youtu.be/OvWttQpM_Qw",
"https://youtu.be/kmiBBUmQZ_M",
"https://youtu.be/L45m1ovty5s",
"https://youtu.be/KSd5XjjFSec",
"https://youtu.be/NA79vPFy6g4"
    ]

    album = "OST DOOM 2016"  # 🔹 Tu peux changer ou mettre None

    print(f"🚀 Lancement du téléchargement pour {len(liste_urls)} vidéo(s).")
    print(f"📁 Fichiers enregistrés dans : {os.path.abspath(dossier_de_sortie)}")

    for i, url in enumerate(liste_urls, start=1):
        print("\n" + "="*50)
        print(f"Traitement de la vidéo {i}/{len(liste_urls)}")
        telecharger_youtube_en_mp3(
            url,
            chemin_sortie=dossier_de_sortie,
            track_number=i,
            album_name=album
        )

    print("\n" + "="*50)
    print("🎉 Tous les téléchargements sont terminés !")
