import os
import shutil
import zipfile
import py7zr
import geopandas as gpd
from pathlib import Path

# --- CONFIGURATION ---
mpk_dir = "mpk_dir"      # Répertoire contenant les fichiers .mpk à traiter
geojson_dir = "geojson_dir"  # Répertoire de sortie pour les GeoJSON
temp_extract_dir = "temp_mpk_extract"

def convert_mpk_to_geojson(mpk_file, output_dir):
    temp_copy_path = None # Initialisation pour le bloc finally
    try:
        # 1. Détection du format et extraction
        is_zip = zipfile.is_zipfile(mpk_file)
        is_7z = py7zr.is_7zfile(mpk_file)

        if not is_zip and not is_7z:
             print(f"Erreur : Le fichier {mpk_file} n'est ni un ZIP ni un 7z valide.")
             return

        # On travaille sur une copie pour éviter de modifier l'original (bonne pratique)
        # et on ajuste l'extension pour la clarté si besoin, mais surtout pour l'extraction
        ext = ".zip" if is_zip else ".7z"
        temp_copy_path = mpk_file.replace('.mpk', ext)
        # Si le nom est identique (ex: fichier déjà .zip), on évite l'écrasement ou l'erreur
        if temp_copy_path != mpk_file:
            shutil.copyfile(mpk_file, temp_copy_path)
        else:
             temp_copy_path = mpk_file # On utilise l'original si l'extension match déjà (peu probable ici avec .mpk)

        # Nettoyage préalable du dossier temporaire
        if os.path.exists(temp_extract_dir):
             try:
                shutil.rmtree(temp_extract_dir)
             except:
                pass
        os.makedirs(temp_extract_dir, exist_ok=True)

        print(f"Extraction de {os.path.basename(mpk_file)} ({'ZIP' if is_zip else '7z'})...")
        
        if is_zip:
            with zipfile.ZipFile(temp_copy_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
        elif is_7z:
            with py7zr.SevenZipFile(temp_copy_path, mode='r') as z:
                z.extractall(path=temp_extract_dir)
        
        # 3. Définition du chemin vers les Shapefiles
        # Basé sur votre structure : commondata/shp4ia
        shp_dir = os.path.join(temp_extract_dir, "commondata", "shp4ia")
        
        if not os.path.exists(shp_dir):
            # Tentative de recherche récursive si le chemin strict n'existe pas
            found_shp_dir = None
            for root, dirs, files in os.walk(temp_extract_dir):
                if "shp4ia" in dirs:
                    found_shp_dir = os.path.join(root, "shp4ia")
                    break
            
            if found_shp_dir:
                 shp_dir = found_shp_dir
            else:
                print(f"Erreur : Le répertoire 'shp4ia' est introuvable dans le package {os.path.basename(mpk_file)}.")
                # Liste le contenu pour debug
                print("Contenu extrait :")
                for root, dirs, files in os.walk(temp_extract_dir):
                    level = root.replace(temp_extract_dir, '').count(os.sep)
                    indent = ' ' * 4 * (level)
                    print(f'{indent}{os.path.basename(root)}/')
                return

        # 4. Création du dossier de sortie final
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 5. Conversion des fichiers .shp
        print(f"--- Conversion de {os.path.basename(mpk_file)} vers : {output_dir} ---")
        count = 0
        for file in os.listdir(shp_dir):
            if file.endswith(".shp"):
                file_path = os.path.join(shp_dir, file)
                
                # Lecture et conversion
                try:
                    gdf = gpd.read_file(file_path)
                    
                    # Correction : Force le format GPS standard (WGS84) si ce n'est pas déjà le cas
                    if gdf.crs is not None:
                        if gdf.crs.to_epsg() != 4326:
                            gdf = gdf.to_crs(epsg=4326)
                    
                    output_name = os.path.splitext(file)[0] + ".json"
                    gdf.to_file(os.path.join(output_dir, output_name), driver='GeoJSON')
                    
                    print(f"  Succès : {file} -> {output_name}")
                    count += 1
                except Exception as e:
                     print(f"  Erreur lors de la conversion de {file} : {e}")


        print(f"--- Terminé pour ce fichier : {count} shapefiles convertis ---")

    except Exception as e:
        print(f"Une erreur générale est survenue pour {mpk_file} : {e}")
    
    finally:
        # Nettoyage des fichiers temporaires
        if temp_copy_path and os.path.exists(temp_copy_path) and temp_copy_path != mpk_file:
            try:
                os.remove(temp_copy_path)
            except:
                pass
        if os.path.exists(temp_extract_dir):
            try:
                shutil.rmtree(temp_extract_dir)
            except:
                pass

def process_all_mpks():
    if not os.path.exists(mpk_dir):
        print(f"Le dossier source '{mpk_dir}' n'existe pas.")
        return

    # Création du dossier global de sortie s'il n'existe pas
    if not os.path.exists(geojson_dir):
        os.makedirs(geojson_dir)

    mpk_files = [f for f in os.listdir(mpk_dir) if f.endswith('.mpk')]
    
    if not mpk_files:
        print(f"Aucun fichier .mpk trouvé dans '{mpk_dir}'.")
        return

    print(f"Traitement de {len(mpk_files)} fichiers .mpk...")
    
    for filename in mpk_files:
        mpk_path = os.path.join(mpk_dir, filename)
        
        # Nom du sous-dossier basé sur le nom du fichier MPK (sans extension)
        sub_dir_name = Path(filename).stem
        current_output_dir = os.path.join(geojson_dir, sub_dir_name)
        
        convert_mpk_to_geojson(mpk_path, current_output_dir)

# Lancement du script
if __name__ == "__main__":
    process_all_mpks()