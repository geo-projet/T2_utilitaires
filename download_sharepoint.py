"""
Téléchargement récursif de fichiers SharePoint (.pdf, .mpk, .gdb).

Usage :
    1. Remplir le fichier .env (SITE_URL et LIBRARY_NAME)
    2. pip install -r requirements.txt
    3. python download_sharepoint.py
    → Un code s'affiche, ouvrir le lien dans le navigateur pour s'authentifier.
"""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote

import msal
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

SITE_URL = os.getenv("SITE_URL", "").rstrip("/")
LIBRARY_NAME = os.getenv("LIBRARY_NAME", "Documents partages")

# Client ID de l'app « Microsoft Office » (première partie, présente dans tous les tenants)
CLIENT_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
AUTHORITY = "https://login.microsoftonline.com/organizations"

EXTENSIONS_CIBLES = {".pdf", ".mpk", ".gdb"}
DOSSIERS_IGNORES = {"Forms", "_private", "_catalogs"}

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "pdf_dir"
MPK_DIR = BASE_DIR / "mpk_dir"
GDB_DIR = BASE_DIR / "gdb_dir"

DOSSIER_PAR_EXT = {
    ".pdf": PDF_DIR,
    ".mpk": MPK_DIR,
    ".gdb": GDB_DIR,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("sharepoint_dl")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler(
    BASE_DIR / "download.log", encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------


def acquire_token_device_code() -> str:
    """Obtient un access token SharePoint via device code flow."""
    sharepoint_host = SITE_URL.split("/sites/")[0] if "/sites/" in SITE_URL else SITE_URL
    scopes = [f"{sharepoint_host}/.default"]

    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        logger.error(
            "Impossible d'initier le device flow : %s",
            flow.get("error_description", ""),
        )
        sys.exit(1)

    print("\n" + "=" * 60)
    print(flow["message"])
    print("=" * 60 + "\n")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Erreur inconnue"))
        logger.error("Échec d'authentification : %s", error)
        sys.exit(1)

    logger.info("Authentification réussie.")
    return result["access_token"]


# ---------------------------------------------------------------------------
# API REST SharePoint helpers
# ---------------------------------------------------------------------------


def sp_get(session: requests.Session, endpoint: str) -> dict:
    """GET sur l'API REST SharePoint, retourne le JSON."""
    url = f"{SITE_URL}/_api/{endpoint}"
    resp = session.get(url)
    resp.raise_for_status()
    raw = resp.json()
    # Normaliser OData verbose (d/results) → format plat (value)
    if "d" in raw:
        inner = raw["d"]
        if "results" in inner:
            return {"value": inner["results"]}
        return inner
    return raw


def sp_get_bytes(session: requests.Session, endpoint: str) -> bytes:
    """GET binaire sur l'API REST SharePoint."""
    url = f"{SITE_URL}/_api/{endpoint}"
    resp = session.get(url)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_path(dest: Path) -> Path:
    """Retourne un chemin unique en ajoutant un suffixe _1, _2, … si nécessaire."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def download_file(session: requests.Session, server_relative_url: str, dest: Path) -> None:
    """Télécharge un fichier SharePoint vers *dest*."""
    dest = unique_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    encoded_url = quote(server_relative_url, safe="/")
    try:
        data = sp_get_bytes(
            session,
            f"web/GetFileByServerRelativeUrl('{encoded_url}')/$value",
        )
        dest.write_bytes(data)
        logger.info("OK  %s", dest.relative_to(BASE_DIR))
    except Exception:
        logger.exception("ERREUR téléchargement → %s", dest)
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass


def download_gdb_folder(session: requests.Session, server_relative_url: str, dest_dir: Path) -> None:
    """Télécharge récursivement le contenu d'un dossier .gdb (File Geodatabase)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    encoded_url = quote(server_relative_url, safe="/")

    # Fichiers
    try:
        data = sp_get(
            session,
            f"web/GetFolderByServerRelativeUrl('{encoded_url}')/Files",
        )
    except Exception:
        logger.exception("ERREUR lecture fichiers dans %s", server_relative_url)
        return

    for item in data.get("value", []):
        name = item["Name"]
        file_url = item["ServerRelativeUrl"]
        download_file(session, file_url, dest_dir / name)

    # Sous-dossiers
    try:
        data = sp_get(
            session,
            f"web/GetFolderByServerRelativeUrl('{encoded_url}')/Folders",
        )
    except Exception:
        logger.exception("ERREUR lecture sous-dossiers dans %s", server_relative_url)
        return

    for item in data.get("value", []):
        sf_name = item["Name"]
        if sf_name in DOSSIERS_IGNORES:
            continue
        download_gdb_folder(session, item["ServerRelativeUrl"], dest_dir / sf_name)


# ---------------------------------------------------------------------------
# Parcours récursif
# ---------------------------------------------------------------------------


def process_folder(session: requests.Session, server_relative_url: str) -> None:
    """Parcourt récursivement un dossier SharePoint et télécharge les fichiers ciblés."""
    encoded_url = quote(server_relative_url, safe="/")

    # --- Fichiers -----------------------------------------------------------
    try:
        data = sp_get(
            session,
            f"web/GetFolderByServerRelativeUrl('{encoded_url}')/Files",
        )
    except Exception:
        logger.exception("ERREUR lecture fichiers dans %s", server_relative_url)
        return

    files_list = data.get("value", [])
    logger.info("  %d fichier(s) dans %s", len(files_list), server_relative_url)
    for item in files_list:
        name: str = item["Name"]
        ext = Path(name).suffix.lower()
        logger.debug("    fichier: %s (ext=%s)", name, ext)
        if ext in EXTENSIONS_CIBLES:
            dest_dir = DOSSIER_PAR_EXT[ext]
            download_file(session, item["ServerRelativeUrl"], dest_dir / name)

    # --- Sous-dossiers ------------------------------------------------------
    try:
        data = sp_get(
            session,
            f"web/GetFolderByServerRelativeUrl('{encoded_url}')/Folders",
        )
    except Exception:
        logger.exception("ERREUR lecture sous-dossiers dans %s", server_relative_url)
        return

    folders_list = data.get("value", [])
    logger.info("  %d sous-dossier(s) dans %s", len(folders_list), server_relative_url)
    for item in folders_list:
        sf_name: str = item["Name"]

        if sf_name in DOSSIERS_IGNORES:
            logger.debug("Ignoré (système) : %s", sf_name)
            continue

        # Dossier .gdb → File Geodatabase complète
        if sf_name.lower().endswith(".gdb"):
            logger.info("GDB dossier détecté : %s", sf_name)
            gdb_dest = unique_path(GDB_DIR / sf_name)
            download_gdb_folder(session, item["ServerRelativeUrl"], gdb_dest)
            continue

        # Sinon → récursion
        logger.debug("Entrée dans : %s", sf_name)
        process_folder(session, item["ServerRelativeUrl"])


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main() -> None:
    if not SITE_URL:
        logger.error("Variable SITE_URL manquante dans .env.")
        sys.exit(1)

    for d in (PDF_DIR, MPK_DIR, GDB_DIR):
        d.mkdir(exist_ok=True)

    # Authentification
    access_token = acquire_token_device_code()

    # Session HTTP avec le token
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json;odata=verbose",
        }
    )

    # Validation de la connexion
    logger.info("Connexion à %s …", SITE_URL)
    try:
        web_data = sp_get(session, "web")
        title = web_data.get("d", {}).get("Title", web_data.get("Title", "?"))
        logger.info("Connecté au site : %s", title)
    except Exception:
        logger.exception("Échec de connexion à SharePoint.")
        sys.exit(1)

    # Déterminer l'URL relative du dossier racine de la bibliothèque
    # On utilise directement le ServerRelativeUrl du dossier, plus fiable
    # que getByTitle (dont le titre peut différer selon la langue).
    site_path = SITE_URL.replace("https://", "").split("/", 1)
    site_relative = "/" + site_path[1] if len(site_path) > 1 else ""
    root_url = f"{site_relative}/{LIBRARY_NAME}"

    # Vérifier que le dossier existe
    try:
        encoded = quote(root_url, safe="/")
        folder_data = sp_get(
            session,
            f"web/GetFolderByServerRelativeUrl('{encoded}')",
        )
        logger.debug("Dossier racine trouvé : %s", root_url)
    except Exception:
        logger.exception(
            "Impossible d'accéder à la bibliothèque « %s » (%s).",
            LIBRARY_NAME,
            root_url,
        )
        sys.exit(1)

    logger.info("Parcours de la bibliothèque « %s » …", LIBRARY_NAME)
    process_folder(session, root_url)
    logger.info("Terminé.")


if __name__ == "__main__":
    main()
