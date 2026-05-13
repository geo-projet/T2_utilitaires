# T2 Utilitaires — Téléchargement SharePoint

Scripts Python pour télécharger des fichiers depuis un site SharePoint Teams et convertir les formats SIG (`.mpk`, `.gpkg`) en GeoJSON.

- `download_sharepoint.py` — parcourt récursivement la bibliothèque SharePoint et télécharge les `.pdf`, `.mpk`, `.gdb` et `.gpkg` dans des dossiers locaux dédiés
- `import_mpk.py` — convertit les Map Packages ArcGIS (`.mpk`) en GeoJSON
- `import_gpkg.py` — convertit les GeoPackages OGC (`.gpkg`) en GeoJSON

## Prérequis

- Python 3.8+
- Accès à un site SharePoint Online

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

## Configuration

Copier et remplir le fichier `.env` :

```env
SITE_URL=https://TONENTREPRISE.sharepoint.com/sites/NOM-DU-SITE
LIBRARY_NAME=Documents partages
```

- **SITE_URL** : URL du site SharePoint Teams
- **LIBRARY_NAME** : nom du dossier de la bibliothèque de documents tel qu'il apparaît dans l'URL (par défaut : `Documents partages`)

## Utilisation

### Télécharger depuis SharePoint

```bash
python download_sharepoint.py
```

Le script affiche un code et un lien. Ouvrir le lien dans un navigateur, entrer le code et se connecter avec son compte Microsoft. Le téléchargement démarre automatiquement après l'authentification.

### Convertir en GeoJSON

```bash
python import_mpk.py    # .mpk  → geojson_dir/<nom>/<shapefile>.json
python import_gpkg.py   # .gpkg → geojson_dir/<nom>/<couche>.json
```

Les deux scripts reprojettent automatiquement les couches en WGS84 (EPSG:4326).

## Fichiers téléchargés

| Extension | Dossier local | Description |
|-----------|---------------|-------------|
| `.pdf`    | `pdf_dir/`    | Documents PDF |
| `.mpk`    | `mpk_dir/`    | Map Packages ArcGIS (archive ZIP/7z de Shapefiles) |
| `.gdb`    | `gdb_dir/`    | File Geodatabases (fichiers ou dossiers) |
| `.gpkg`   | `gpkg_dir/`   | GeoPackages OGC (SQLite multi-couches) |

Les dossiers `.gdb` (File Geodatabases) sont détectés et téléchargés intégralement avec leur structure interne préservée.

## Logs

- **Console** : messages INFO (progression, erreurs)
- **`download.log`** : journal complet DEBUG avec horodatage

## Reprise des téléchargements

Si un fichier existe déjà localement, il est **passé** (log `SKIP`) — aucun retéléchargement, aucun suffixe `_1`. Cela permet de relancer le script après une interruption pour récupérer uniquement les fichiers manquants, y compris à l'intérieur d'un dossier `.gdb` partiellement téléchargé.

## Notes

- L'authentification utilise le **device code flow** Microsoft, compatible avec le MFA
- Aucun mot de passe n'est stocké localement
- Les dossiers système SharePoint (`Forms`, `_private`, `_catalogs`) sont ignorés automatiquement
