import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import matplotlib.image as mpimg
import os
import pandas as pd

def generate_global_maps(df):
    paths = {}
    titles = {'t': 'TEMPÉRATURE (°C)', 'ff': 'VENT (KM/H)', 'rr1': 'PLUIE (MM)'}
    # Choix de colormaps bien visibles sur un fond carte
    cmaps = {'t': 'plasma', 'ff': 'viridis', 'rr1': 'YlGnBu'}
    
    bg_image_name = 'Corse_region_relief_location_map.jpg'
    
    # --- CORRECTION 2 : AJUSTEMENT DE L'EXTENT ---
    # Nouvelles coordonnées pour essayer de recalert les points (Cap Corse était trop haut)
    # On remonte la limite Nord (43.12) et on ajuste légèrement l'Ouest (8.50)
    map_extent = [8.50, 9.65, 41.20, 43.12]

    for var, cmap in cmaps.items():
        # Figure plus haute pour s'adapter à la forme de la Corse
        fig, ax = plt.subplots(figsize=(9, 12))
        
        # 1. Affichage du fond de carte
        if os.path.exists(bg_image_name):
            img = mpimg.imread(bg_image_name)
            # zorder=0 pour le mettre tout au fond
            ax.imshow(img, extent=map_extent, aspect='auto', zorder=0)
        else:
            print(f"⚠️ Attention : Image '{bg_image_name}' non trouvée. Fond bleu utilisé.")
            ax.set_facecolor('#e0f2fe')

        # 2. Tracer les points (stations)
        sc = ax.scatter(df['lon'], df['lat'], c=df[f'{var}_pred'], cmap=cmap, 
                        s=200, edgecolors='white', linewidth=1.5, zorder=2, alpha=0.9)

        # 3. Ajouter les annotations
        unique_stations = df.drop_duplicates(subset=['station'])
        for _, row in unique_stations.iterrows():
            label_text = f"{row['station']}\n{row[f'{var}_pred']:.1f}"
            ax.annotate(label_text,
                        (row['lon'], row['lat']),
                        xytext=(8, 8),
                        textcoords='offset points',
                        fontsize=9, color='black', fontweight='bold',
                        zorder=3,
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cccccc", alpha=0.8))

        # 4. Finitions du graphique
        ax.set_xlim(map_extent[0], map_extent[1])
        ax.set_ylim(map_extent[2], map_extent[3])
        plt.title(f"PRÉVISIONS CORSE - {titles[var]}", fontsize=16, fontweight='bold', pad=15)
        plt.axis('off')

        # --- CORRECTION 1 : COLORBAR INTERNE EN BAS À GAUCHE ---
        # Création d'un axe inséré [pos_x, pos_y, largeur, hauteur] en relatif (0-1)
        # Placé en bas à gauche (0.05, 0.05)
        cax = ax.inset_axes([0.05, 0.05, 0.4, 0.03])
        
        # Création de la colorbar horizontale dans cet axe
        cbar = plt.colorbar(sc, cax=cax, orientation='horizontal')
        
        # Style de la colorbar
        cbar.set_label(titles[var], fontsize=10, fontweight='bold', labelpad=5)
        cbar.ax.tick_params(labelsize=9)
        # Ajout d'un fond blanc semi-transparent à l'axe de la colorbar pour lisibilité sur la mer
        cax.set_facecolor('white')
        cax.patch.set_alpha(0.8)
        # -------------------------------------------------------

        path = f"map_{var}.png"
        plt.savefig(path, bbox_inches='tight', dpi=150, transparent=True)
        plt.close()
        paths[var] = path
    return paths

# La fonction generate_station_charts reste inchangée
def generate_station_charts(df, station_name):
    data = df[df['station'] == station_name].sort_values('forecast_time')
    paths = {}
    today = datetime.now().strftime('%d/%m/%Y')
    configs = {'t': ('Température', '#ff4b2b', '°C'), 'ff': ('Vent', '#00d2ff', 'km/h'), 'rr1': ('Pluie', '#a8ff78', 'mm')}
    for var, (label, color, unit) in configs.items():
        plt.figure(figsize=(10, 4), facecolor='white')
        ax = plt.gca()
        plt.plot(data['forecast_time'], data[f'{var}_pred'], marker='o', color=color, linewidth=2)
        plt.fill_between(data['forecast_time'], data[f'{var}_pred'], color=color, alpha=0.1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.title(f"PRÉVISIONS {label.upper()} - {station_name} ({today})", fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.ylabel(unit)
        path = f"chart_{var}_{station_name}.png"
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        paths[var] = path
    return paths