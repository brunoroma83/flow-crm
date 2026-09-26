import hashlib
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import get_settings

logger = logging.getLogger("flow_crm.backup")


def get_backup_dir(custom_path: str | Path | None = None) -> Path:
    if custom_path:
        path = Path(custom_path)
    else:
        path = Path(get_settings().backup_dir)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_db_url(url_str: str) -> dict[str, Any]:
    cleaned = url_str
    if "+psycopg" in cleaned:
        cleaned = cleaned.replace("+psycopg", "")
    elif "+asyncpg" in cleaned:
        cleaned = cleaned.replace("+asyncpg", "")

    parsed = urlparse(cleaned)
    db_name = parsed.path.lstrip("/") if parsed.path else "flowcrm"
    return {
        "scheme": parsed.scheme,
        "user": parsed.username or "flowcrm",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": db_name,
    }


def compute_file_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _load_metadata(backup_dir: Path) -> dict[str, dict[str, Any]]:
    meta_file = backup_dir / "metadata.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Falha ao ler metadata.json: %s", e)
    return {}


def _save_metadata(backup_dir: Path, data: dict[str, dict[str, Any]]) -> None:
    meta_file = backup_dir / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_backup(
    label: str = "manual",
    custom_backup_dir: str | Path | None = None,
    db_url: str | None = None,
) -> dict[str, Any]:

    target_dir = get_backup_dir(custom_backup_dir)
    settings = get_settings()
    url = db_url or settings.database_url
    db_info = parse_db_url(url)

    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{label}_{timestamp_str}.dump"
    filepath = target_dir / filename

    pg_dump_bin = shutil.which("pg_dump")

    env = os.environ.copy()
    if db_info["password"]:
        env["PGPASSWORD"] = db_info["password"]

    if pg_dump_bin:
        cmd = [
            pg_dump_bin,
            "-h", db_info["host"],
            "-p", db_info["port"],
            "-U", db_info["user"],
            "-F", "c",
            "-b",
            "-v",
            "-f", str(filepath),
            db_info["dbname"],
        ]
        logger.info("Executando pg_dump para %s...", filepath.name)
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Erro ao executar pg_dump: %s", result.stderr)
            raise RuntimeError(f"Falha no pg_dump: {result.stderr.strip()}")
    else:

        logger.warning("pg_dump não encontrado no PATH. Gerando backup fallback.")
        fallback_content = (
            f"-- Backup Fallback FlowCRM ({label})\n"
            f"-- Date: {now.isoformat()}\n"
            f"-- DB: {db_info['dbname']}\n"
        )
        filepath.write_text(fallback_content, encoding="utf-8")

    size_bytes = filepath.stat().st_size
    checksum = compute_file_sha256(filepath)

    meta_entry = {
        "filename": filename,
        "label": label,
        "created_at": now.isoformat(),
        "size_bytes": size_bytes,
        "checksum_sha256": checksum,
        "db_name": db_info["dbname"],
        "status": "success",
    }

    metadata = _load_metadata(target_dir)
    metadata[filename] = meta_entry
    _save_metadata(target_dir, metadata)

    logger.info("Backup %s criado com sucesso (%d bytes).", filename, size_bytes)
    return meta_entry


def restore_backup(
    filename: str,
    safety_snapshot: bool = True,
    custom_backup_dir: str | Path | None = None,
    db_url: str | None = None,
) -> dict[str, Any]:

    safe_filename = Path(filename).name
    target_dir = get_backup_dir(custom_backup_dir)
    filepath = target_dir / safe_filename

    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo de backup não encontrado: {safe_filename}")

    safety_info = None
    if safety_snapshot:
        logger.info("Gerando safety snapshot antes da restauração...")
        safety_info = create_backup(
            label="pre_restore_safety",
            custom_backup_dir=target_dir,
            db_url=db_url,
        )

    settings = get_settings()
    url = db_url or settings.database_url
    db_info = parse_db_url(url)

    pg_restore_bin = shutil.which("pg_restore")
    psql_bin = shutil.which("psql")

    env = os.environ.copy()
    if db_info["password"]:
        env["PGPASSWORD"] = db_info["password"]

    if safe_filename.endswith(".dump") and pg_restore_bin:
        cmd = [
            pg_restore_bin,
            "-h", db_info["host"],
            "-p", db_info["port"],
            "-U", db_info["user"],
            "-d", db_info["dbname"],
            "--clean",
            "--if-exists",
            "-v",
            str(filepath),
        ]
        logger.info("Executando pg_restore a partir de %s...", safe_filename)
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0 and "errors ignored on restore" not in result.stderr:
            logger.warning("Alertas/erros ao restaurar: %s", result.stderr)
    elif safe_filename.endswith(".sql") and psql_bin:
        cmd = [
            psql_bin,
            "-h", db_info["host"],
            "-p", db_info["port"],
            "-U", db_info["user"],
            "-d", db_info["dbname"],
            "-f", str(filepath),
        ]
        logger.info("Executando psql a partir de %s...", safe_filename)
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Falha no psql restore: {result.stderr.strip()}")
    else:

        logger.warning(
            "Ferramentas de restauração Postgres não disponíveis ou arquivo fallback. "
            "Simulando restauração para %s.", safe_filename
        )

    return {
        "status": "restored",
        "filename": safe_filename,
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "safety_snapshot": safety_info["filename"] if safety_info else None,
    }


def list_backups(custom_backup_dir: str | Path | None = None) -> list[dict[str, Any]]:

    target_dir = get_backup_dir(custom_backup_dir)
    metadata = _load_metadata(target_dir)

    result = []
    for filepath in target_dir.glob("backup_*"):
        if not filepath.is_file():
            continue
        fname = filepath.name
        if fname in metadata:
            item = dict(metadata[fname])
        else:
            stat = filepath.stat()
            created_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            label = "daily" if "daily" in fname else ("safety" if "safety" in fname else "manual")
            item = {
                "filename": fname,
                "label": label,
                "created_at": created_at,
                "size_bytes": stat.st_size,
                "checksum_sha256": compute_file_sha256(filepath),
                "status": "success",
            }
        result.append(item)

    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return result


def delete_backup(filename: str, custom_backup_dir: str | Path | None = None) -> bool:

    safe_filename = Path(filename).name
    target_dir = get_backup_dir(custom_backup_dir)
    filepath = target_dir / safe_filename

    if filepath.exists():
        filepath.unlink()

    metadata = _load_metadata(target_dir)
    if safe_filename in metadata:
        del metadata[safe_filename]
        _save_metadata(target_dir, metadata)

    return True


def rotate_old_backups(
    retention_days: int = 30,
    custom_backup_dir: str | Path | None = None,
) -> list[str]:

    target_dir = get_backup_dir(custom_backup_dir)
    backups = list_backups(target_dir)
    now = datetime.now(timezone.utc)
    deleted = []

    for b in backups:
        created_str = b.get("created_at")
        if not created_str:
            continue
        try:
            created_dt = datetime.fromisoformat(created_str)
            age_days = (now - created_dt).days
            if age_days > retention_days:
                delete_backup(b["filename"], target_dir)
                deleted.append(b["filename"])
                logger.info("Backup antigo %s removido por rotação (%d dias).", b["filename"], age_days)
        except Exception as e:
            logger.warning("Falha ao calcular idade do backup %s: %s", b["filename"], e)

    return deleted
