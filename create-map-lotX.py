import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import json

# --- Configuration ---
# Modifiez ces noms de fichiers selon vos besoins
CSV_INPUT_FILE = 'lot2-1.csv'
HTML_OUTPUT_FILE = 'carte_interactive.html'
# -------------------

def create_map_from_csv(csv_path, output_path):
    """
    Génère une carte HTML interactive à partir d'un fichier CSV d'inventaire.
    """
    print(f"Lecture du fichier CSV : {csv_path}...")
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        print("Tentative avec l'encodage 'latin-1'...")
        df = pd.read_csv(csv_path, encoding='latin-1', on_bad_lines='skip')

    # Nettoyage des données
    df['site'] = df['site'].str.strip()
    df.dropna(subset=['site'], inplace=True)
    
    print("Regroupement des données par site...")
    # Compte total par site
    site_counts = df['site'].value_counts().reset_index()
    site_counts.columns = ['site', 'total_count']

    # Compte détaillé par type de matériel pour les info-bulles
    tooltip_data = df.groupby('site')['LIBELLE'].apply(
        lambda x: x.value_counts().to_dict()
    ).to_dict()

    # --- Géocodage des sites ---
    print("Géocodage des adresses (cela может prendre du temps)...")
    geolocator = Nominatim(user_agent="inventory_map_generator")
    # Limiteur pour ne pas surcharger le service de géocodage (1 requête/seconde)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    locations = {}
    for site in site_counts['site']:
        try:
            location = geocode(f"{site}, France")
            if location:
                locations[site] = (location.latitude, location.longitude)
                print(f"  - Coordonnées trouvées pour : {site}")
            else:
                locations[site] = None
                print(f"  - ATTENTION : Coordonnées non trouvées pour : {site}")
            time.sleep(0.5) # Pause supplémentaire par politesse
        except Exception as e:
            print(f"  - ERREUR de géocodage pour {site}: {e}")
            locations[site] = None
            
    site_counts['coords'] = site_counts['site'].map(locations)
    site_counts.dropna(subset=['coords'], inplace=True)

    # --- Création de la carte ---
    if site_counts.empty:
        print("Aucune coordonnée valide n'a été trouvée. Impossible de créer la carte.")
        return

    print("Création de la carte Folium...")
    map_center = site_counts['coords'].iloc[0]
    m = folium.Map(location=map_center, zoom_start=8)

    # Ajout des sites sur la carte
    js_sites_array = []
    for _, row in site_counts.iterrows():
        site_name = row['site']
        total_count = row['total_count']
        coords = row['coords']

        # Création du contenu de l'info-bulle
        tooltip_html = f"<b>&Eacute;quipement pour {site_name} :</b><br><ul>"
        details = tooltip_data.get(site_name, {})
        # Trier par nombre décroissant
        sorted_details = sorted(details.items(), key=lambda item: item[1], reverse=True)
        for libelle, count in sorted_details:
            tooltip_html += f"<li>{libelle}: {count}</li>"
        tooltip_html += "</ul>"

        # Ajout du cercle
        circle = folium.Circle(
            location=coords,
            radius=total_count * 50, # Rayon proportionnel au nombre d'items
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.6,
            tooltip=tooltip_html
        )
        circle.add_to(m)

        # Ajout du libellé
        label_html = f'<div style="font-size:12px; color:black; font-weight:bold">{site_name} ({total_count})</div>'
        marker = folium.Marker(
            location=coords,
            icon=folium.DivIcon(html=label_html, icon_size=(150, 36), icon_anchor=(0, 0))
        )
        marker.add_to(m)

        # Préparation des données pour le JavaScript
        js_sites_array.append({
            "name": f"{site_name} ({total_count})",
            "marker_name": marker.get_name(),
            "circle_name": circle.get_name()
        })
        
    # --- Ajout du CSS et JavaScript pour l'interactivité ---
    print("Ajout du CSS et du JavaScript pour l'interactivité...")

    # On utilise les noms des variables Leaflet générées par Folium
    js_dynamic_part = "const sites_map = {\n"
    for site in js_sites_array:
        js_dynamic_part += f'    "{site["name"]}": {{ marker: {site["marker_name"]}, circle: {site["circle_name"]} }},\n'
    js_dynamic_part += "};\n"

    # Le code HTML/CSS/JS est injecté dans le template de la carte
    custom_html_css_js = f"""
    <style>
        #site-list-container {{
            position: absolute;
            top: 10px;
            right: 10px;
            background-color: rgba(255, 255, 255, 0.9);
            padding: 15px;
            border-radius: 8px;
            max-height: 80%;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .site-item {{ display: flex; align-items: center; margin-bottom: 5px; }}
        .site-item input[type="checkbox"] {{ margin-right: 8px; cursor: pointer; }}
        .site-item label {{ cursor: pointer; margin: 0; }}
        .leaflet-tooltip {{ font-size: 14px; }}
    </style>
    
    <div id="site-list-container">
        <h5>Sites à visiter :</h5>
        <div id="site-list-content"></div>
    </div>

    <script type="text/javascript">
        function toggleSiteVisibility(siteName) {{
            const site = sites_map[siteName];
            if (!site) return;

            const isChecked = document.getElementById(`checkbox-${siteName}`).checked;
            const opacity = isChecked ? 1 : 0; // 1 pour afficher, 0 pour masquer

            site.marker.setOpacity(opacity);
            site.circle.setStyle({{ opacity: opacity, fillOpacity: opacity * 0.6 }});
            
            const markerElement = site.marker.getElement();
            if (markerElement) {{
                markerElement.style.opacity = opacity;
            }}
        }}

        function generateSiteList() {{
            const container = document.getElementById('site-list-content');
            container.innerHTML = ''; // Vider la liste

            const siteNames = Object.keys(sites_map);
            siteNames.sort(); // Trier par ordre alphabétique

            siteNames.forEach(siteName => {{
                const siteDiv = document.createElement('div');
                siteDiv.className = 'site-item';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `checkbox-${siteName}`;
                checkbox.checked = true; // Tous visibles par défaut
                checkbox.addEventListener('change', () => toggleSiteVisibility(siteName));

                const label = document.createElement('label');
                label.htmlFor = `checkbox-${siteName}`;
                label.textContent = siteName;

                siteDiv.appendChild(checkbox);
                siteDiv.appendChild(label);
                container.appendChild(siteDiv);
            }});
        }}
        
        // Attendre que la carte soit prête
        document.addEventListener("DOMContentLoaded", function() {{
            {js_dynamic_part}
            generateSiteList();
        }});
    </script>
    """
    
    m.get_root().html.add_child(folium.Element(custom_html_css_js))

    # Sauvegarde du fichier
    m.save(output_path)
    print(f"\\nCarte générée avec succès ! Fichier sauvegardé sous : {output_path}")


if __name__ == '__main__':
    create_map_from_csv(CSV_INPUT_FILE, HTML_OUTPUT_FILE)
