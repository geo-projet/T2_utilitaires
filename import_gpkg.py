import os
import fiona
import geopandas as gpd
from pathlib import Path

# --- CONFIGURATION ---
gpkg_dir = "gpkg_dir"        # Répertoire contenant les fichiers .gpkg à traiter
geojson_dir = "geojson_dir"  # Répertoire de sortie pour les GeoJSON


def convert_gpkg_to_geojson(gpkg_file, output_dir):
    try:
        # 1. Lister les couches du GeoPackage (base SQLite, pas une archive)
        try:
            layers = fiona.listlayers(gpkg_file)
        except Exception as e:
            print(f"Erreur : Impossible de lire les couches de {os.path.basename(gpkg_file)} : {e}")
            return

        if not layers:
            print(f"Aucune couche trouvée dans {os.path.basename(gpkg_file)}.")
            return

        # 2. Création du dossier de sortie final
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 3. Conversion des couches
        print(f"--- Conversion de {os.path.basename(gpkg_file)} vers : {output_dir} ---")
        count = 0
        for layer in layers:
            try:
                gdf = gpd.read_file(gpkg_file, layer=layer)

                # Correction : Force le format GPS standard (WGS84) si ce n'est pas déjà le cas
                if gdf.crs is not None:
                    if gdf.crs.to_epsg() != 4326:
                        gdf = gdf.to_crs(epsg=4326)

                output_name = layer + ".json"
                gdf.to_file(os.path.join(output_dir, output_name), driver="GeoJSON")

                print(f"  Succès : {layer} -> {output_name}")
                count += 1
            except Exception as e:
                print(f"  Erreur lors de la conversion de la couche {layer} : {e}")

        print(f"--- Terminé pour ce fichier : {count} couches converties ---")

    except Exception as e:
        print(f"Une erreur générale est survenue pour {gpkg_file} : {e}")


def process_all_gpkgs():
    if not os.path.exists(gpkg_dir):
        print(f"Le dossier source '{gpkg_dir}' n'existe pas.")
        return

    # Création du dossier global de sortie s'il n'existe pas
    if not os.path.exists(geojson_dir):
        os.makedirs(geojson_dir)

    gpkg_files = [f for f in os.listdir(gpkg_dir) if f.lower().endswith(".gpkg")]

    if not gpkg_files:
        print(f"Aucun fichier .gpkg trouvé dans '{gpkg_dir}'.")
        return

    print(f"Traitement de {len(gpkg_files)} fichiers .gpkg...")

    for filename in gpkg_files:
        gpkg_path = os.path.join(gpkg_dir, filename)

        # Nom du sous-dossier basé sur le nom du fichier GPKG (sans extension)
        sub_dir_name = Path(filename).stem
        current_output_dir = os.path.join(geojson_dir, sub_dir_name)

        convert_gpkg_to_geojson(gpkg_path, current_output_dir)


# Lancement du script
if __name__ == "__main__":
    process_all_gpkgs()
