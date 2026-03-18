# T2 Utilitaires — Téléchargement SharePoint

Script Python qui se connecte à un site SharePoint Teams, parcourt récursivement tous les répertoires et télécharge les fichiers `.pdf`, `.mpk` et `.gdb` dans des dossiers locaux dédiés.

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

```bash
python download_sharepoint.py
```

Le script affiche un code et un lien. Ouvrir le lien dans un navigateur, entrer le code et se connecter avec son compte Microsoft. Le téléchargement démarre automatiquement après l'authentification.

## Fichiers téléchargés

| Extension | Dossier local | Description |
|-----------|---------------|-------------|
| `.pdf`    | `pdf_dir/`    | Documents PDF |
| `.mpk`    | `mpk_dir/`    | Map Packages ArcGIS |
| `.gdb`    | `gdb_dir/`    | File Geodatabases (fichiers ou dossiers) |

Les dossiers `.gdb` (File Geodatabases) sont détectés et téléchargés intégralement avec leur structure interne préservée.

## Logs

- **Console** : messages INFO (progression, erreurs)
- **`download.log`** : journal complet DEBUG avec horodatage

## Gestion des collisions

Si un fichier du même nom existe déjà, un suffixe `_1`, `_2`, etc. est ajouté automatiquement.

## Notes

- L'authentification utilise le **device code flow** Microsoft, compatible avec le MFA
- Aucun mot de passe n'est stocké localement
- Les dossiers système SharePoint (`Forms`, `_private`, `_catalogs`) sont ignorés automatiquement
