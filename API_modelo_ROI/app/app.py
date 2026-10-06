"""API H7 (Flask)

EPO CodeFest-friendly Flask service to:
  - Deploy, update and delete ML models (artifact files: .pkl / .joblib).
  - Generate an input/output manifest (contract) from scikit-learn pipelines.
  - Expose REST endpoints to query the schema and run predictions by context.

Notes
-----
* The business logic is preserved. Only comments/docstrings are translated to English.
* The service is designed for reproducible model deployment and traceable operations (checksum, backups).
"""


import datetime
import hashlib
import json
import os
import pickle
import time
import traceback
import uuid
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

import Utilidades as ut
from LogH7 import LogH7
from ModeloML import ModeloML as MML
from TextDB import TextDB
from pathlib import Path

ALLOWED_MODEL_EXTS = {".pkl", ".joblib"}
MAX_UPLOAD_MB = 200  # ajusta si quieres

def file_checksum_sha256(path: str) -> str:
    """CodeFest-friendly description for `file_checksum_sha256`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_model_filename(original_name: str) -> str:
    """CodeFest-friendly description for `safe_model_filename`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return secure_filename(original_name)


def save_uploaded_model_with_hash_date(file_storage, timestamp: datetime.datetime) -> tuple[str, str, str]:
    """CodeFest-friendly description for `save_uploaded_model_with_hash_date`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    models_dir = str(MODELOS_DIR)

    original_name = file_storage.filename or "model.pkl"
    _, ext = os.path.splitext(original_name)
    ext = (ext or ".pkl").lower()

    # Escribimos a un temporal mientras calculamos el hash (evita cargar todo en memoria).
    tmp_name = f"tmp_{uuid.uuid4().hex}{ext}"
    tmp_abs_path = os.path.join(models_dir, tmp_name)

    h = hashlib.sha256()
    with open(tmp_abs_path, "wb") as out_f:
        for chunk in iter(lambda: file_storage.stream.read(1024 * 1024), b""):
            h.update(chunk)
            out_f.write(chunk)

    sha256_hex = h.hexdigest()
    ts = timestamp.strftime("%Y%m%d_%H%M%S")
    final_name = f"{sha256_hex}_{ts}{ext}"
    final_abs_path = os.path.join(models_dir, final_name)

    # Por si se repite la misma subida en el mismo segundo, evitamos sobreescritura.
    if os.path.exists(final_abs_path):
        final_name = f"{sha256_hex}_{ts}_{uuid.uuid4().hex[:6]}{ext}"
        final_abs_path = os.path.join(models_dir, final_name)

    os.replace(tmp_abs_path, final_abs_path)
    rel_path = f"modelos/{final_name}"
    return rel_path, final_abs_path, sha256_hex


def create_backup_zip(rel_artifact_path: str, contexto: str, modelo: str, timestamp: datetime.datetime) -> str | None:
    """CodeFest-friendly description for `create_backup_zip`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    if not rel_artifact_path:
        return None

    artifact_abs = str((BASE_DIR / rel_artifact_path).resolve())
    if not os.path.exists(artifact_abs):
        return None

    safe_contexto = secure_filename(contexto) or "contexto"
    safe_modelo = secure_filename(modelo) or "modelo"
    stamp = timestamp.strftime("%Y%m%d_%H%M%S")

    # Si es un fichero, intentamos añadir una huella corta para diferenciar rápidamente
    short_hash = ""
    try:
        if os.path.isfile(artifact_abs):
            h = hashlib.sha256()
            with open(artifact_abs, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            short_hash = h.hexdigest()[:12]
    except Exception:
        short_hash = ""

    zip_name = f"{safe_contexto}__{safe_modelo}__{short_hash + '__' if short_hash else ''}{stamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_name)

    try:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(artifact_abs):
                # Guardar como artifact/<nombre_original>
                arcname = os.path.join("artifact", os.path.basename(artifact_abs))
                zf.write(artifact_abs, arcname)
            else:
                # Directory: añadir recursivamente
                base = Path(artifact_abs)
                for fp in base.rglob("*"):
                    if fp.is_file():
                        rel_inside = fp.relative_to(base)
                        arcname = os.path.join("artifact", str(rel_inside).replace("\\", "/"))
                        zf.write(str(fp), arcname)
        return zip_name
    except Exception:
        return None


def is_artifact_path_shared(rel_path: str, exclude_context: str | None = None) -> bool:
    """CodeFest-friendly description for `is_artifact_path_shared`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    try:
        registros = db.select(lambda record: (record.get("ruta") == rel_path))
        if exclude_context is None:
            return len(registros) > 1
        return any(r.get("contexto") != exclude_context for r in registros)
    except Exception:
        # En caso de duda, tratamos como compartido para no borrar accidentalmente.
        return True

def validate_model_file(file_storage) -> tuple[bool, str]:
    """CodeFest-friendly description for `validate_model_file`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    name = file_storage.filename or ""
    _, ext = os.path.splitext(name.lower())
    if ext not in ALLOWED_MODEL_EXTS:
        return False, f"Extensión no permitida: {ext}. Permitidas: {sorted(ALLOWED_MODEL_EXTS)}"
    return True, ""

def extract_pipeline_from_loaded(obj):
    """CodeFest-friendly description for `extract_pipeline_from_loaded`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    if hasattr(obj, "predict"):
        # si es wrapper, suele tener .model con Pipeline
        if hasattr(obj, "modelo"):
            return obj.modelo
        # si ya es pipeline
        return obj
    raise ValueError("El objeto cargado no parece un modelo con predict()")

def get_expected_feature_names_from_pipeline(pipeline) -> list[str]:
    """CodeFest-friendly description for `get_expected_feature_names_from_pipeline`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    # forma estándar sklearn
    if hasattr(pipeline, "feature_names_in_"):
        return list(pipeline.feature_names_in_)

    # fallback: buscar en pasos
    for _, step in getattr(pipeline, "named_steps", {}).items():
        if hasattr(step, "feature_names_in_"):
            return list(step.feature_names_in_)

    raise ValueError("No se pudo determinar feature_names_in_ del pipeline")

def generate_manifest_from_model_file(model_path: str, contexto: str, modelo_nombre: str) -> dict:
    """CodeFest-friendly description for `generate_manifest_from_model_file`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    # Loads robusta: joblib suele ser mejor para sklearn
    try:
        loaded = joblib.load(model_path)
    except Exception:
        # fallback a pickle por si acaso
        with open(model_path, "rb") as f:
            loaded = pickle.load(f)

    pipeline = extract_pipeline_from_loaded(loaded)
    expected_features = get_expected_feature_names_from_pipeline(pipeline)

    manifest = {
        "manifest_version": "1.0",
        "context": contexto,
        "model_name": modelo_nombre,
        "created_at": datetime.datetime.now().isoformat(),
        "framework": {
            "sklearn_version": getattr(sklearn, "__version__", "unknown"),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        },
        "input_schema": {
            "type": "tabular",
            "expected_features": expected_features,
            "allow_extra_features": False,
            "fill_missing_with_null": True,
        },
        "output_schema": {
            "type": "regression",
            "target": "pred",
            "shape": "n"
        },
        "artifact": {
            "path": model_path.replace("\\", "/"),
            "sha256": file_checksum_sha256(model_path),
        }
    }
    return manifest

def dataframe_from_json_payload(payload):
    """CodeFest-friendly description for `dataframe_from_json_payload`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    if payload is None:
        raise ValueError("JSON vacío o inválido")

    if isinstance(payload, list):
        return pd.DataFrame(payload)

    if isinstance(payload, dict):
        any_list = any(isinstance(v, (list, tuple)) for v in payload.values())
        return pd.DataFrame(payload) if any_list else pd.DataFrame([payload])

    raise ValueError(f"Formato JSON no soportado: {type(payload)}")

def align_features(df: pd.DataFrame, expected_cols: list[str]) -> tuple[pd.DataFrame, list[str], list[str]]:
    """CodeFest-friendly description for `align_features`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    df2 = df.copy()

    extras = [c for c in df2.columns if c not in expected_cols]
    if extras:
        df2 = df2.drop(columns=extras)

    missing = [c for c in expected_cols if c not in df2.columns]
    for c in missing:
        df2[c] = np.nan

    df2 = df2.loc[:, expected_cols]
    return df2, extras, missing



def contract_expected_cols(schema_in: dict) -> list[str]:
    """CodeFest-friendly description for `contract_expected_cols`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    feats = schema_in.get("features", [])
    return [f["name"] for f in feats if "name" in f]

def validate_against_contract(df: pd.DataFrame, schema_in: dict):
    """CodeFest-friendly description for `validate_against_contract`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    expected = contract_expected_cols(schema_in)
    required = [f["name"] for f in schema_in.get("features", []) if f.get("required")]

    extras = [c for c in df.columns if c not in expected]
    missing_required = [c for c in required if c not in df.columns]
    missing_any = [c for c in expected if c not in df.columns]

    allow_extra = bool(schema_in.get("allow_extra_features", False))
    fill_missing = bool(schema_in.get("fill_missing_with_null", True))

    if missing_required:
        return False, {
            "reason": "missing_required_features",
            "missing_required": missing_required,
            "expected": expected
        }

    if extras and not allow_extra:
        return False, {
            "reason": "extra_features_not_allowed",
            "extras": extras,
            "expected": expected
        }

    # Alineado
    df2 = df.copy()

    if extras and allow_extra:
        # si permites extras, puedes ignorarlos igualmente
        df2 = df2.drop(columns=[c for c in extras if c in df2.columns])

    if fill_missing:
        for c in missing_any:
            if c not in df2.columns:
                df2[c] = np.nan
    else:
        # si no permites rellenar, cualquier missing (aunque no required) es error
        missing_non_required = [c for c in expected if c not in df2.columns]
        if missing_non_required:
            return False, {
                "reason": "missing_features",
                "missing": missing_non_required,
                "expected": expected
            }

    df2 = df2.loc[:, expected]  # orden exacto
    return True, {
        "aligned_df": df2,
        "extras": extras,
        "missing_filled": [c for c in expected if c not in df.columns]
    }


def dataframe_from_json_payload(payload):
    """CodeFest-friendly description for `dataframe_from_json_payload`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    if payload is None:
        raise ValueError("JSON vacío o inválido")

    if isinstance(payload, list):
        # lista de registros
        return pd.DataFrame(payload)

    if isinstance(payload, dict):
        # si es dict de listas -> DataFrame directo; si es escalar -> 1 fila
        any_list = any(isinstance(v, (list, tuple)) for v in payload.values())
        return pd.DataFrame(payload) if any_list else pd.DataFrame([payload])

    raise ValueError(f"Formato JSON no soportado: {type(payload)}")


def get_expected_feature_names(pipeline):
    """CodeFest-friendly description for `get_expected_feature_names`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    if hasattr(pipeline, "feature_names_in_"):
        return list(pipeline.feature_names_in_)

    # Si no está en pipeline, puede estar en el primer paso que valida nombres
    for step_name, step_obj in getattr(pipeline, "named_steps", {}).items():
        if hasattr(step_obj, "feature_names_in_"):
            return list(step_obj.feature_names_in_)

    raise ValueError("No se pudo determinar feature_names_in_ del modelo/pipeline")


def align_features(df, expected_cols):
    """CodeFest-friendly description for `align_features`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    df2 = df.copy()

    extras = [c for c in df2.columns if c not in expected_cols]
    if extras:
        df2 = df2.drop(columns=extras)

    missing = [c for c in expected_cols if c not in df2.columns]
    for c in missing:
        df2[c] = np.nan

    return df2.loc[:, expected_cols], extras, missing

# Backend section (primero crear app)
app = Flask(__name__)

# --- Paths base consistentes (no dependen del CWD) ---
BASE_DIR = Path(app.root_path)          # en Docker: /app/app
DATABASE_DIR = BASE_DIR / "database"
MODELOS_DIR = BASE_DIR / "modelos"
BACKUP_DIR = BASE_DIR / "backups"

DATABASE_DIR.mkdir(parents=True, exist_ok=True)
MODELOS_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Configure el módulo de registro (ya con rutas consistentes)
db_conf = TextDB(str(DATABASE_DIR / "database_config.txdb"),
                 ["nombre", "propiedad", "valor", "parametro", "ruta"])
trazas_mensajes = LogH7(db_conf)
trazas_mensajes.escribir_info("Iniciamos API Rest para H7")

# Initialize database General
db = TextDB(str(DATABASE_DIR / "database.txdb"),
            ["modelo", "contexto", "input", "output", "fecha", "checksum", "ruta"])



# Directory donde se almacenan los backups (ZIP)
BACKUP_DIR = os.path.join(app.root_path, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)


@app.route("/")
def root():
    """CodeFest-friendly description for `root`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return redirect(url_for("index"))

@app.route('/backendAdmin')
def index():
    """CodeFest-friendly description for `index`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return render_template('index.html')

@app.route('/backendAdmin/menulateral')
def menulateral():
    """CodeFest-friendly description for `menulateral`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return render_template('menu_lateral.html')

@app.route('/backendAdmin/deploy')
def deploy_models():
    """CodeFest-friendly description for `deploy_models`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return render_template('desplegar_modelos.html')

@app.route('/backendAdmin/modify', methods=['POST'])
def modify_models():
    """CodeFest-friendly description for `modify_models`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    data = request.form  # Esto devolverá un diccionario de los datos
    #context = request.args.get('context')
    contexto = data.get('contexto')
    try:
        datos_tabla = db.select(lambda record: (record[1] == contexto))
        datos_tabla[0]['input'] = str(json.loads(datos_tabla[0]['input']))
        datos_tabla[0]['output'] = str(json.loads(datos_tabla[0]['output']))
        return render_template('modificar_modelos.html', datos_tabla=datos_tabla)
    except Exception as e:
        trazas_mensajes.escribir_error('Error accediendo a la página de modificacion de modelos', e)
        return render_template('manejador_error.html')

@app.route("/api/health", methods=["GET"])
def api_health():
    """CodeFest-friendly description for `api_health`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    try:
        # Estado básico del servicio
        now = datetime.datetime.now().isoformat()

        # Check simple de “dependencias”/recursos mínimos
        modelos_dir = str(MODELOS_DIR)
        db_path = str(DATABASE_DIR / "database.txdb")

        status = {
            "status": "ok",
            "service": "api_h7",
            "time": now,
            "checks": {
                "modelos_dir_exists": os.path.isdir(modelos_dir),
                "db_exists": os.path.isfile(db_path),
            }
        }

        # Si falla algo crítico, marcamos degraded
        if not all(status["checks"].values()):
            status["status"] = "degraded"

        return jsonify(status), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "api_h7",
            "error": str(e)
        }), 500

@app.route('/backendAdmin/delete', methods=['POST'])
def delete_models():
    """CodeFest-friendly description for `delete_models`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    data = request.form  # Esto devolverá un diccionario de los datos
    #context = request.args.get('context')
    contexto = data.get('contexto')
    try:
        datos_tabla = db.select(lambda record: (record[1] == contexto))
        datos_tabla[0]['input'] = str(json.loads(datos_tabla[0]['input']))
        datos_tabla[0]['output'] = str(json.loads(datos_tabla[0]['output']))
        return render_template('eliminar_modelos.html', datos_tabla=datos_tabla)
    except Exception as e:
        trazas_mensajes.escribir_error('Error accediendo a la página de eliminacion de modelos', e)
        return render_template('manejador_error.html')

@app.route('/api_h7/<context>/schema', methods=['GET'])
def get_schema(context):
    """CodeFest-friendly description for `get_schema`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    datos_api_rest_context = [i['contexto'] for i in db.tabulate()]
    if context not in datos_api_rest_context:
        return jsonify({"error": "No existe modelo asociado a este contexto"}), 404

    rec = db.select(lambda record: (record[1] == context))[0]
    try:
        manifest = json.loads(rec.get("input")) if rec.get("input") else {}
    except Exception:
        return jsonify({"error": "Manifest corrupto"}), 500

    return jsonify({
        "context": context,
        "model": rec.get("modelo"),
        "updated_at": rec.get("fecha"),
        "checksum": rec.get("checksum"),
        "manifest": manifest
    }), 200


   
@app.route('/backendAdmin/info', methods=['POST'])
def info_models():
    """CodeFest-friendly description for `info_models`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    datos_tabla = db.select(lambda record: (record[1] == request.form["contexto"]))
    return render_template('info_modelos.html', datos_tabla=datos_tabla)

@app.route('/backendAdmin/estados')
def estado_models():
    """CodeFest-friendly description for `estado_models`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    datos_tabla = db.tabulate()
    return render_template('estado_modelos.html', datos_tabla=datos_tabla)

@app.route('/backendAdmin/cabecera')
def cabecera():
    """CodeFest-friendly description for `cabecera`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return render_template('cabecera.html')

@app.route('/backendAdmin/manejador_error')
def manejador_error():
    """CodeFest-friendly description for `manejador_error`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return render_template('manejador_error.html')

@app.route('/backendAdmin/documentacion')
def documentacion():
    """CodeFest-friendly description for `documentacion`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    return render_template('documentacion.html')


@app.route('/backendAdmin/upload', methods=['POST'])
def upload():
    """CodeFest-friendly description for `upload`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    timestamp = datetime.datetime.now()

    try:
        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename:
            return render_template('manejador_error.html'), 400

        ok, msg = validate_model_file(archivo)
        if not ok:
            trazas_mensajes.escribir_error("Upload rechazado", msg)
            return render_template('manejador_error.html'), 400

        contexto = request.form.get("contexto", "").strip()
        modelo_nombre = request.form.get("modelo", "").strip()

        if not contexto or not modelo_nombre:
            trazas_mensajes.escribir_error("Faltan campos", "modelo/contexto vacíos")
            return render_template('manejador_error.html'), 400
        # Guardar fichero con nombre hash+fecha (evita colisiones y artefactos compartidos)
        rel_path, abs_path, _sha256 = save_uploaded_model_with_hash_date(archivo, timestamp)

        # Generar manifest desde el pipeline del model guardado
        manifest = generate_manifest_from_model_file(abs_path, contexto, modelo_nombre)

        # Guardar en DB: input = manifest, output = output_schema (o el manifest completo)
        db.insert([
            modelo_nombre,
            contexto,
            json.dumps(manifest, ensure_ascii=False),
            json.dumps(manifest.get("output_schema", {"type": "regression", "target": "pred"}), ensure_ascii=False),
            timestamp.strftime("%d/%m/%Y %H:%M:%S"),
            manifest["artifact"]["sha256"],
            rel_path
        ])

        trazas_mensajes.escribir_info(f"Modelo '{modelo_nombre}' desplegado en contexto '{contexto}'")

        return estado_models(), 200

    except Exception:
        trazas_mensajes.escribir_error("Error en upload", traceback.format_exc())
        return render_template('manejador_error.html'), 500


@app.route('/backendAdmin/update_upload', methods=['POST'])
def update_upload():
    """CodeFest-friendly description for `update_upload`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    timestamp = datetime.datetime.now()

    try:
        contexto = request.form.get("contexto", "").strip()
        modelo_nombre = request.form.get("modelo", "").strip()

        if not contexto or not modelo_nombre:
            return render_template('manejador_error.html'), 400

        datos_modelo_antiguo = db.select(lambda record: (record[1] == contexto))
        if not datos_modelo_antiguo:
            trazas_mensajes.escribir_error("Update sobre contexto inexistente", contexto)
            return render_template('manejador_error.html'), 404


        old_rel_path = datos_modelo_antiguo[0].get("ruta")
        old_abs_path = os.path.join(os.getcwd(), old_rel_path) if old_rel_path else None
        old_is_shared = is_artifact_path_shared(old_rel_path, exclude_context=contexto) if old_rel_path else True

        # Backup del artefacto anterior (ZIP)
        try:
            zip_name = create_backup_zip(old_rel_path, contexto, modelo_nombre, timestamp)
            if not zip_name:
                trazas_mensajes.escribir_error("Backup previo no generado", f"Ruta: {old_rel_path}")
        except Exception:
            trazas_mensajes.escribir_error("Error en backup previo", traceback.format_exc())
        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename:
            return render_template('manejador_error.html'), 400

        ok, msg = validate_model_file(archivo)
        if not ok:
            trazas_mensajes.escribir_error("Update upload rechazado", msg)
            return render_template('manejador_error.html'), 400
        # Guardar el nuevo fichero con nombre hash+fecha (evita colisiones y artefactos compartidos)
        rel_path, abs_path, _sha256 = save_uploaded_model_with_hash_date(archivo, timestamp)

        # Generar manifest nuevo
        manifest = generate_manifest_from_model_file(abs_path, contexto, modelo_nombre)

        # Actualizar registro DB
        db.update(
            lambda record: (record[1] == contexto),
            [
                modelo_nombre,
                contexto,
                json.dumps(manifest, ensure_ascii=False),
                json.dumps(manifest.get("output_schema", {"type": "regression", "target": "pred"}), ensure_ascii=False),
                timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                manifest["artifact"]["sha256"],
                rel_path
            ]
        )


        # Limpieza del artefacto anterior:
        # si el fichero anterior NO está compartido por otros contexts, podemos eliminarlo
        # porque ya se ha generado un backup en /old_models.
        try:
            if old_abs_path and os.path.isfile(old_abs_path) and (not old_is_shared) and (old_rel_path != rel_path):
                os.remove(old_abs_path)
        except Exception:
            trazas_mensajes.escribir_error("No se pudo eliminar el artefacto anterior tras actualizar", traceback.format_exc())

        trazas_mensajes.escribir_info(f"Modelo '{modelo_nombre}' actualizado en contexto '{contexto}'")

        return estado_models(), 200

    except Exception:
        trazas_mensajes.escribir_error("Error en update_upload", traceback.format_exc())
        return render_template('manejador_error.html'), 500


@app.route('/backendAdmin/do_delete', methods=['POST'])
def do_delete():
    """CodeFest-friendly description for `do_delete`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    timestamp = datetime.datetime.now()
    datos_modelo_antiguo = db.select(lambda record: (record[1] == request.form["contexto"]))
                                     
    if( ut.validar_json_ins(request.form["input"]) and ut.validar_json_ins(request.form["output"])):
        # Creamos fichero JSON entrada y salida y firma
        try:
            zip_name = create_backup_zip(datos_modelo_antiguo[0].get("ruta"), request.form["contexto"], datos_modelo_antiguo[0].get("modelo", "modelo"), timestamp)
            if not zip_name:
                trazas_mensajes.escribir_error("Backup no generado", f"Ruta: {datos_modelo_antiguo[0].get('ruta')}")
        except Exception as e:
            trazas_mensajes.escribir_error("Error generando backup ZIP", e)
            trazas_mensajes.escribir_error(
                "No se pudo realizar el backup del modelo previo",
                f"Ruta: {datos_modelo_antiguo[0].get('ruta')}"
            )
        directorio_actual = os.getcwd()
        ruta_completa = os.path.join(directorio_actual, datos_modelo_antiguo[0].get("ruta"))
    
        try:
            rel_path = datos_modelo_antiguo[0].get("ruta")
            compartido = is_artifact_path_shared(rel_path, exclude_context=request.form["contexto"]) if rel_path else True

            if compartido:
                # Caso: el mismo fichero está referenciado por otros contexts.
                # No se elimina el artefacto físico, pero sí el registro de este context.
                db.delete(lambda record: (record[1] == request.form["contexto"]))
                trazas_mensajes.escribir_info(
                    f"Se elimina el registro del contexto '{request.form['contexto']}', pero se conserva el fichero compartido: {ruta_completa}"
                )
            else:
                if os.path.isfile(ruta_completa):
                    os.remove(ruta_completa)
                    db.delete(lambda record: (record[1] == request.form["contexto"]))
                    trazas_mensajes.escribir_info(f"El archivo {ruta_completa} ha sido eliminado exitosamente.")
                else:
                    db.delete(lambda record: (record[1] == request.form["contexto"]))
                    trazas_mensajes.escribir_info(f"El archivo {ruta_completa} no existe. Se elimina el registro en BBDD.")
        except Exception as e:
            trazas_mensajes.escribir_error(
                f"Hubo problemas con la eliminación del fichero {request.form['contexto']} en la BBDD",
                e)
            return manejador_error()    
    return estado_models()

@app.route('/imagen/<path:filename>')
def imagen(filename):
    """CodeFest-friendly description for `imagen`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    directorio_imagenes = os.path.join(app.root_path, 'static', 'images')
    return send_from_directory(directorio_imagenes, filename)


@app.route('/api_h7/<context>', methods=['POST'])
def get_dynamic_data(context):
    """CodeFest-friendly description for `get_dynamic_data`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    try:

        datos_api_rest_context = [i['contexto'] for i in db.tabulate()]
        if context not in datos_api_rest_context:
            return jsonify({"error": "No existe modelo asociado a este contexto"}), 404


        rec = db.select(lambda record: (record[1] == context))[0]
        ruta_rel = rec.get("ruta")  # ej: "modelos/xxx.pkl"

        abs_model_path = os.path.abspath(os.path.join(app.root_path, ruta_rel))

        # Log diagnóstico (INFO)
        trazas_mensajes.escribir_info(
            f"[LOAD MODEL] context={context} "
            f"ruta_rel={ruta_rel} "
            f"ruta_abs={abs_model_path} "
            f"exists={os.path.isfile(abs_model_path)} "
            f"cwd={os.getcwd()}"
        )

        if not os.path.isfile(abs_model_path):
            return jsonify({
                "error": "Modelo no encontrado en disco",
                "ruta_rel": ruta_rel,
                "ruta_abs": abs_model_path,
                "cwd": os.getcwd()
            }), 500


        json_data = request.get_json(silent=True)
        if json_data is None:
            return jsonify({"error": "JSON inválido o vacío"}), 400


        try:
            df_in = dataframe_from_json_payload(json_data)
        except Exception as e:
            return jsonify({
                "error": "Formato de JSON no soportado",
                "detalle": str(e)
            }), 400


        try:
            model = MML.cargar_modelo(abs_model_path)
        except Exception:
            trazas_mensajes.escribir_error(
                f"[ERROR LOAD MODEL] {abs_model_path}",
                traceback.format_exc()
            )
            return jsonify({
                "error": "Modelo incorrecto",
                "ruta_abs": abs_model_path,
                "trace": traceback.format_exc()
            }), 500


        try:
            manifest = json.loads(rec.get("input")) if rec.get("input") else {}
            expected_cols = manifest.get("input_schema", {}).get("expected_features")
        except Exception:
            expected_cols = None

        # Fallback al pipeline si el manifest no existe
        if not expected_cols:
            pipeline = getattr(model, "modelo", None)
            if pipeline is None:
                return jsonify({"error": "Modelo sin pipeline accesible"}), 500
            expected_cols = get_expected_feature_names_from_pipeline(pipeline)


        missing_required = [c for c in expected_cols if c not in df_in.columns]
        if missing_required:
            return jsonify({
                "error": "Faltan columnas requeridas",
                "missing_features": missing_required,
                "expected_features": expected_cols
            }), 422


        extras = [c for c in df_in.columns if c not in expected_cols]
        if extras:
            df_in = df_in.drop(columns=extras)

        df_aligned = df_in.loc[:, expected_cols]


        try:
            output = model.predecir(df_aligned)
        except Exception:
            trazas_mensajes.escribir_error(
                "[ERROR PREDICT]",
                traceback.format_exc()
            )
            return jsonify({
                "error": "Error durante la predicción",
                "trace": traceback.format_exc()
            }), 500


        arr = np.asarray(output)
        if arr.ndim == 0:
            arr = arr.reshape(1)
        elif arr.ndim > 1:
            arr = arr.reshape(-1)


        return jsonify({
            "context": context,
            "n_rows": int(df_aligned.shape[0]),
            "pred": arr.tolist(),
            "dropped_extra_features": extras,
            "model_sha256": rec.get("checksum")
        }), 200

    except Exception:
        trazas_mensajes.escribir_error(
            "[ERROR UNEXPECTED /api_h7/<context>]",
            traceback.format_exc()
        )
        return jsonify({
            "error": "Error interno no controlado",
            "trace": traceback.format_exc()
        }), 500


@app.route('/static/backups/<path:filename>')
def backup(filename):
    """CodeFest-friendly description for `backup`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    directorio_imagenes = BACKUP_DIR
    return send_from_directory(directorio_imagenes, filename)


@app.route('/backendAdmin/gestion_backups')
def directory_backups():
    """CodeFest-friendly description for `directory_backups`.

    Business logic preserved; this docstring is an English translation placeholder.
    """
    # Path del directorio que deseas mostrar
    directory_path = BACKUP_DIR

    # Lista de archivos en el directorio
    files = os.listdir(directory_path)
    fechas = [ut.obtener_fecha_escritura(f'{directory_path}/{fichero}') for fichero in files]
    datos = zip(fechas, files)

    # Renderizar una plantilla HTML para mostrar los archivos
    return render_template('directory_listing.html', datos=datos)


if __name__ == '__main__':
    # En entrega/producción se ejecuta sin modo DEBUG.
    app.run(port=8000, debug=False)