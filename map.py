import pandas as pd
import folium
from geopy.geocoders import Nominatim
import time
import os
import math

# --- Fichiers ---
input_csv = "lot2.csv"
cache_file = "cache_geocoding.csv"
output_map = "carte_sites.html"

# --- Lire le CSV ---
df = pd.read_csv(input_csv)
df["site"] = df["site"].str.strip()

# --- Compter les occurrences avant suppression des doublons ---
occurrences = df["site"].value_counts().to_dict()

# --- Supprimer les doublons pour géocoder une seule fois chaque ville ---
df_unique = df.drop_duplicates(subset=["site"])

# --- Charger le cache si existant ---
if os.path.exists(cache_file):
    cache = pd.read_csv(cache_file)
else:
    cache = pd.DataFrame(columns=["site", "lat", "lon"])

# --- Initialiser le géocodeur ---
geolocator = Nominatim(user_agent="map_script")

# --- Liste finale des coordonnées ---
coords = []

for site in df_unique["site"]:
    if site in cache["site"].values:
        lat = cache.loc[cache["site"] == site, "lat"].values[0]
        lon = cache.loc[cache["site"] == site, "lon"].values[0]
        coords.append({"site": site, "lat": lat, "lon": lon, "count": occurrences[site]})
    else:
        try:
            location = geolocator.geocode(site + ", France")
            if location:
                lat, lon = location.latitude, location.longitude
                coords.append({"site": site, "lat": lat, "lon": lon, "count": occurrences[site]})
                cache = pd.concat([cache, pd.DataFrame([{"site": site, "lat": lat, "lon": lon}])], ignore_index=True)
                time.sleep(1)
            else:
                print(f"⚠️ Ville introuvable : {site}")
        except Exception as e:
            print(f"Erreur pour {site} : {e}")

# --- Sauvegarder le cache ---
cache.to_csv(cache_file, index=False)

# --- Conversion en DataFrame ---
coords_df = pd.DataFrame(coords)

# --- Carte centrée sur la moyenne des points ---
map_center = [coords_df["lat"].mean(), coords_df["lon"].mean()]
carte = folium.Map(location=map_center, zoom_start=7)

# --- Ajouter les cercles proportionnels ---
from folium.features import DivIcon
import math

for _, row in coords_df.iterrows():
    # Rayon du cercle proportionnel à la racine carrée
    radius = math.sqrt(row["count"]) * 500

    # Cercle bleu
    folium.Circle(
        location=[row["lat"], row["lon"]],
        radius=radius,
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.6,
    ).add_to(carte)

    # Texte fixe (nom + occurrences) au centre du cercle
    folium.map.Marker(
        location=[row["lat"], row["lon"]],
        icon=DivIcon(
            icon_size=(150,36),
            icon_anchor=(0,0),
            html=f'<div style="font-size:12px; color:black; font-weight:bold">{row["site"]} ({row["count"]})</div>',
        )
    ).add_to(carte)


# --- Sauvegarde de la carte ---
carte.save(output_map)
print(f"✅ Carte générée avec cercles proportionnels : ouvrez '{output_map}' dans un navigateur.")
