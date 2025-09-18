from pytube import Playlist

# Lien de la playlist
playlist_url = "https://www.youtube.com/watch?v=vyA1z2A-lhU&list=PL3-Zr0Ym0Fgw9G6368AMfMKp9TR1ToaqR&index=2&ab_channel=Nox"

# Charger la playlist
playlist = Playlist(playlist_url)

# Extraire les vidéos et les mettre au bon format
video_urls = [f"\"https://youtu.be/{video.video_id}\"," for video in playlist.videos]

# Afficher
for url in video_urls:
    print(url)
