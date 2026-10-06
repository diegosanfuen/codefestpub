"""utilidades.py

EPO CodeFest style utilities
----------------------------
Collection of small helper functions used across the project.

Design goals (CodeFest / demo context):
- Keep helpers explicit and readable.
- Avoid hidden side effects.
- Prefer standard library only (easy to audit, easy to deploy).

Scope:
- JSON validation helpers
- Temporary workspace management
- File metadata utilities
- Lightweight backup / compression helpers
- Checksum calculation for integrity verification

Important:
These utilities are intentionally simple. They are suitable for demos,
PoCs and controlled environments, not for high-concurrency production systems.
"""

import json
import zipfile
import os
import shutil
from pathlib import Path
import hashlib
import datetime
from typing import Any


def validar_json_ins(json_obj: Any) -> bool:
    """Validate that an object can be serialized to JSON.

    This checks *serialization* (json.dumps), not parsing.
    Useful when validating Python objects before persistence or transport.
    """
    try:
        json.dumps(json_obj)
        return True
    except (TypeError, ValueError):
        return False


def validar_json(json_str: str) -> bool:
    """Validate that a string contains valid JSON."""
    try:
        json.loads(json_str)
        return True
    except ValueError:
        return False


def crear_ruta_temporal() -> Path:
    """Create (if needed) and return a temporary working directory.

    The directory is created relative to the current working directory
    and named `_tmp`.
    """
    directorio_actual = os.getcwd()
    directorio_temporal = Path(directorio_actual) / "_tmp"
    os.makedirs(directorio_temporal, exist_ok=True)
    return directorio_temporal


def obtener_fecha_escritura(nombre_archivo: str) -> str:
    """Return the file modification timestamp as a formatted string."""
    fecha_modificacion = os.path.getmtime(nombre_archivo)
    fecha_datetime = datetime.datetime.fromtimestamp(fecha_modificacion)
    return fecha_datetime.strftime("%d/%m/%Y-%H:%M")


def eliminar_ficheros_ruta_temporal() -> None:
    """Delete all files inside the temporary directory."""
    ruta_temporal = Path(os.getcwd()) / "_tmp"
    if not ruta_temporal.exists():
        return

    for archivo in ruta_temporal.iterdir():
        if archivo.is_file():
            archivo.unlink()


def eliminar_ruta_temporal() -> None:
    """Remove the temporary directory entirely."""
    directorio_temporal = Path(os.getcwd()) / "_tmp"
    if directorio_temporal.exists():
        shutil.rmtree(directorio_temporal)


def comprimir_backup(ruta: str | Path, archivo_salida: str | Path) -> None:
    """Compress a file or directory into a ZIP archive."""
    ruta = Path(ruta)
    archivo_salida = Path(archivo_salida)

    with zipfile.ZipFile(archivo_salida, "w", zipfile.ZIP_DEFLATED) as zipf:
        if ruta.is_file():
            zipf.write(ruta, ruta.name)
        else:
            for root, _, archivos in os.walk(ruta):
                for archivo in archivos:
                    ruta_completa = Path(root) / archivo
                    zipf.write(
                        ruta_completa,
                        ruta_completa.relative_to(ruta),
                    )


def copiar_modelo_y_ficheros(archivo_modelo: str) -> None:
    """Create a simple backup of a model file.

    Workflow:
    - Create temporary workspace.
    - Copy model file into the workspace.
    - Compress it into a ZIP archive under `old_models/`.
    - Clean up temporary files.
    """
    tmp_dir = crear_ruta_temporal()

    # Resolve paths
    directorio_actual = Path(os.getcwd())
    ruta_old_models = directorio_actual / "old_models"
    ruta_old_models.mkdir(exist_ok=True)

    ruta_archivo_modelo = directorio_actual / archivo_modelo
    ruta_copia = tmp_dir / ruta_archivo_modelo.name

    # Copy model into temporary workspace
    shutil.copy(ruta_archivo_modelo, ruta_copia)

    # Create ZIP backup
    archivo_zip = ruta_old_models / "backup_model.zip"
    comprimir_backup(ruta_copia, archivo_zip)

    # Cleanup
    eliminar_ruta_temporal()


def calcular_checksum(archivo: str | Path) -> str:
    """Calculate and return the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    archivo = Path(archivo)

    with archivo.open("rb") as f:
        for bloque in iter(lambda: f.read(4096), b""):
            hash_md5.update(bloque)

    return hash_md5.hexdigest()
