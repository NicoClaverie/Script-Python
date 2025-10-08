import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# --- Configuration ---
CSV_INPUT_FILE = r'C:\Users\Nico\Documents\test\lot2-1.csv'
HTML_OUTPUT_FILE = r'carte_interactive.html'
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
    df.dropna(subset=['site', 'LIBELLE'], inplace=True)
    
    print("Regroupement des données par site...")
    site_counts = df['site'].value_counts().reset_index()
    site_counts.columns = ['site', 'total_count']

    # ==================== CORRECTIF FINAL ====================
    # Remplacement de la méthode groupby() qui posait problème par une boucle manuelle plus robuste
    
    print("Construction du dictionnaire des équipements...")
    tooltip_data = {}
    for site in df['site'].unique():
        # Pour chaque site, on filtre le dataframe, on compte les LIBELLE et on stocke le résultat
        counts_dict = df[df['site'] == site]['LIBELLE'].value_counts().to_dict()
        tooltip_data[site] = counts_dict
    
    # =========================================================

    print("Géocodage des adresses (cela peut prendre du temps)...")
    geolocator = Nominatim(user_agent="inventory_map_generator_final")
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
        except Exception as e:
            print(f"  - ERREUR de géocodage pour {site}: {e}")
            locations[site] = None
            
    site_counts['coords'] = site_counts['site'].map(locations)
    site_counts.dropna(subset=['coords'], inplace=True)

    if site_counts.empty:
        print("Aucune coordonnée valide n'a été trouvée. Impossible de créer la carte.")
        return

    print("Création de la carte Folium...")
    map_center = site_counts['coords'].apply(pd.Series).mean().tolist()
    m = folium.Map(location=map_center, zoom_start=8)

    js_sites_array = []
    for _, row in site_counts.iterrows():
        site_name = row['site']
        total_count = row['total_count']
        coords = row['coords']

        tooltip_html = f"<b>&Eacute;quipement pour {site_name} :</b><br><ul>"
        details = tooltip_data.get(site_name, {})
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

        label_html = f'<div style="font-size:12px; color:black; font-weight:bold">{site_name} ({total_count})</div>'
        marker = folium.Marker(
            location=coords,
            icon=folium.DivIcon(html=label_html, icon_size=(150, 36), icon_anchor=(-10, 10))
        ).add_to(m)

        js_sites_array.append({
            "name": f"{site_name} ({total_count})",
            "marker_name": marker.get_name(),
            "circle_name": circle.get_name()
        })
        
    print("Ajout du CSS et du JavaScript pour l'interactivité...")

    js_dynamic_part = ""
    for site in js_sites_array:
        js_dynamic_part += f'"{site["name"]}": {{ marker: {site["marker_name"]}, circle: {site["circle_name"]} }},\n'

    map_var_name = m.get_name()

    custom_html_css_js = f"""
    <style>
        #site-list-container {{
            position: absolute; top: 10px; right: 10px;
            background-color: rgba(255, 255, 255, 0.9);
            padding: 15px; border-radius: 8px; max-height: 80%;
            overflow-y: auto; z-index: 1000;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .site-item {{ display: flex; align-items: center; margin-bottom: 5px; }}
        .site-item input[type="checkbox"] {{ margin-right: 8px; cursor: pointer; }}
        .site-item label {{ cursor: pointer; margin: 0; }}
        .leaflet-tooltip {{ font-size: 14px; }}
    </style>
    
    <div id="site-list-container">
        <h5>Sites visités :</h5>
        <div id="site-list-content"></div>
    </div>

    <script type="text/javascript">
        document.addEventListener("DOMContentLoaded", function() {{
            
            const sites_map = {{
                {js_dynamic_part}
            }};

            // Nouvelle fonction pour envoyer les mises à jour au serveur
            function updateSiteStatusOnServer(siteName, isChecked) {{
                fetch('http://localhost:3000/api/update', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ name: siteName, checked: isChecked }}),
                }})
                .catch(error => console.error('Erreur de mise à jour:', error));
            }}

            function toggleSiteVisibility(siteName, isChecked) {{
                const site = sites_map[siteName];
                if (!site) return;

                const mapObject = {map_var_name};

                if (isChecked) {{ // Si coché, on retire
                    mapObject.removeLayer(site.circle);
                    mapObject.removeLayer(site.marker);
                }} else {{ // Si décoché, on ajoute
                    site.circle.addTo(mapObject);
                    site.marker.addTo(mapObject);
                }}
            }}

            async function initializeMapState() {{
                let siteStates = {{}};
                try {{
                    const response = await fetch('http://localhost:3000/api/status');
                    if (response.ok) {{
                        siteStates = await response.json();
                    }}
                }} catch (error) {{
                    console.error("Serveur non disponible. L'état des cases ne sera pas sauvegardé.", error);
                }}

                const container = document.getElementById('site-list-content');
                if (!container) return;
                container.innerHTML = '';

                const siteNames = Object.keys(sites_map);
                siteNames.sort();

                siteNames.forEach(siteName => {{
                    const isChecked = siteStates[siteName] || false;

                    const siteDiv = document.createElement('div');
                    siteDiv.className = 'site-item';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `checkbox-${{siteName}}`;
                    checkbox.checked = isChecked;
                    
                    checkbox.addEventListener('change', () => {{
                        const newState = checkbox.checked;
                        toggleSiteVisibility(siteName, newState);
                        updateSiteStatusOnServer(siteName, newState);
                    }});

                    const label = document.createElement('label');
                    label.htmlFor = `checkbox-${{siteName}}`;
                    label.textContent = siteName;

                    siteDiv.appendChild(checkbox);
                    siteDiv.appendChild(label);
                    container.appendChild(siteDiv);
                    
                    // Appliquer l'état initial à la carte
                    toggleSiteVisibility(siteName, isChecked);
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
