import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# --- Configuration ---
CSV_INPUT_FILE = r'C:\\Users\\CLAVERIE\\Documents\\Script-Python\\ressource\\match pour HTML.csv'
HTML_OUTPUT_FILE = r'C:\\Users\\CLAVERIE\\Documents\\Script-Python\\ressource\\carte_interactive_lot3.html'
# -------------------

def create_map_from_csv(csv_path, output_path):
    """
    Génère une carte HTML interactive à partir d'un fichier CSV d'inventaire.
    """
    print(f"Lecture du fichier CSV : {csv_path}...")
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    except Exception:
        print("Encodage UTF-8 échoué, tentative avec 'latin-1'...")
        df = pd.read_csv(csv_path, encoding='latin-1', on_bad_lines='skip')

    # Nettoyage des noms de colonnes (enlève les espaces ET les guillemets)
    df.columns = df.columns.str.strip().str.replace('"', '', regex=False)

    # Nettoyage des données dans les colonnes
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.replace('\r\n', ' ', regex=False).str.replace('\n', ' ', regex=False).str.strip()

    # S'assurer que les colonnes essentielles ne sont pas vides
    df.dropna(subset=['Site', 'LIBELLE'], inplace=True)
    
    print("Regroupement des données par Site...")
    Site_counts = df['Site'].value_counts().reset_index()
    Site_counts.columns = ['Site', 'total_count']

    # ==================== CORRECTIF FINAL ====================
    # Remplacement de la méthode groupby() qui posait problème par une boucle manuelle plus robuste
    
    print("Construction du dictionnaire des équipements...")
    tooltip_data = {}
    for Site in df['Site'].unique():
        # Pour chaque Site, on filtre le dataframe, on compte les LIBELLE et on stocke le résultat
        counts_dict = df[df['Site'] == Site]['LIBELLE'].value_counts().to_dict()
        tooltip_data[Site] = counts_dict
    
    # =========================================================

    print("Géocodage des adresses (cela peut prendre du temps)...")
    geolocator = Nominatim(user_agent="inventory_map_generator_final")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    locations = {}
    for Site in Site_counts['Site']:
        try:
            location = geocode(f"{Site}, France")
            if location:
                locations[Site] = (location.latitude, location.longitude)
                print(f"  - Coordonnées trouvées pour : {Site}")
            else:
                locations[Site] = None
                print(f"  - ATTENTION : Coordonnées non trouvées pour : {Site}")
        except Exception as e:
            print(f"  - ERREUR de géocodage pour {Site}: {e}")
            locations[Site] = None
            
    Site_counts['coords'] = Site_counts['Site'].map(locations)
    Site_counts.dropna(subset=['coords'], inplace=True)

    if Site_counts.empty:
        print("Aucune coordonnée valide n'a été trouvée. Impossible de créer la carte.")
        return

    print("Création de la carte Folium...")
    map_center = Site_counts['coords'].apply(pd.Series).mean().tolist()
    m = folium.Map(location=map_center, zoom_start=8)

    js_Sites_array = []
    for _, row in Site_counts.iterrows():
        Site_name = row['Site']
        total_count = row['total_count']
        coords = row['coords']

        tooltip_html = f"<b>&Eacute;quipement pour {Site_name} :</b><br><ul>"
        details = tooltip_data.get(Site_name, {})
        sorted_details = sorted(details.items(), key=lambda item: item[1], reverse=True)
        for libelle, count in sorted_details:
            tooltip_html += f"<li>{libelle}: {count}</li>"
        tooltip_html += "</ul>"

        circle = folium.Circle(
            location=coords,
            radius=total_count * 50 + 200,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.5,
            tooltip=tooltip_html
        ).add_to(m)

        label_html = f'<div style="font-size:12px; color:black; font-weight:bold">{Site_name} ({total_count})</div>'
        marker = folium.Marker(
            location=coords,
            icon=folium.DivIcon(html=label_html, icon_size=(150, 36), icon_anchor=(-10, 10))
        ).add_to(m)

        js_Sites_array.append({
            "name": f"{Site_name} ({total_count})",
            "marker_name": marker.get_name(),
            "circle_name": circle.get_name()
        })
        
    print("Ajout du CSS et du JavaScript pour l'interactivité...")

    js_dynamic_part = ""
    for Site in js_Sites_array:
        js_dynamic_part += f'"{Site["name"]}": {{ marker: {Site["marker_name"]}, circle: {Site["circle_name"]} }},\n'

    map_var_name = m.get_name()

    custom_html_css_js = f"""
    <style>
        #Site-list-container {{
            position: absolute; top: 10px; right: 10px;
            background-color: rgba(255, 255, 255, 0.9);
            padding: 15px; border-radius: 8px; max-height: 80%;
            overflow-y: auto; z-index: 1000;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .Site-item {{ display: flex; align-items: center; margin-bottom: 5px; }}
        .Site-item input[type="checkbox"] {{ margin-right: 8px; cursor: pointer; }}
        .Site-item label {{ cursor: pointer; margin: 0; }}
        .leaflet-tooltip {{ font-size: 14px; }}
    </style>
    
    <div id="Site-list-container">
        <h5>Sites visités :</h5>
        <div id="Site-list-content"></div>
    </div>

    <script type="text/javascript">
        document.addEventListener("DOMContentLoaded", function() {{
            
            const Sites_map = {{
                {js_dynamic_part}
            }};

            // Nouvelle fonction pour envoyer les mises à jour au serveur
            function updateSiteStatusOnServer(SiteName, isChecked) {{
                fetch('http://localhost:3000/api/update', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name: SiteName, checked: isChecked }}),
                }})
                .catch(error => console.error('Erreur de mise à jour:', error));
            }}

            function toggleSiteVisibility(SiteName, isChecked) {{
                const Site = Sites_map[SiteName];
                if (!Site) return;

                const mapObject = {map_var_name};

                if (isChecked) {{ // Si coché, on retire
                    mapObject.removeLayer(Site.circle);
                    mapObject.removeLayer(Site.marker);
                }} else {{ // Si décoché, on ajoute
                    Site.circle.addTo(mapObject);
                    Site.marker.addTo(mapObject);
                }}
            }}

            async function initializeMapState() {{
                let SiteStates = {{}};
                try {{
                    const response = await fetch('http://localhost:3000/api/status');
                    if (response.ok) {{
                        SiteStates = await response.json();
                    }}
                }} catch (error) {{
                    console.error("Serveur non disponible. L'état des cases ne sera pas sauvegardé.", error);
                }}

                const container = document.getElementById('Site-list-content');
                if (!container) return;
                container.innerHTML = '';

                const SiteNames = Object.keys(Sites_map);
                SiteNames.sort();

                SiteNames.forEach(SiteName => {{
                    const isChecked = SiteStates[SiteName] || false;

                    const SiteDiv = document.createElement('div');
                    SiteDiv.className = 'Site-item';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `checkbox-${{SiteName}}`;
                    checkbox.checked = isChecked;
                    
                    checkbox.addEventListener('change', () => {{
                        const newState = checkbox.checked;
                        toggleSiteVisibility(SiteName, newState);
                        updateSiteStatusOnServer(SiteName, newState);
                    }});

                    const label = document.createElement('label');
                    label.htmlFor = `checkbox-${{SiteName}}`;
                    label.textContent = SiteName;

                    SiteDiv.appendChild(checkbox);
                    SiteDiv.appendChild(label);
                    container.appendChild(SiteDiv);
                    
                    // Appliquer l'état initial à la carte
                    toggleSiteVisibility(SiteName, isChecked);
                }});
            }}
            
            initializeMapState();
        }});
    </script>
    """
    
    m.get_root().html.add_child(folium.Element(custom_html_css_js))

    m.save(output_path)
    print(f"\\nCarte générée avec succès ! Fichier sauvegardé sous : {output_path}")

if __name__ == '__main__':
    create_map_from_csv(CSV_INPUT_FILE, HTML_OUTPUT_FILE)
