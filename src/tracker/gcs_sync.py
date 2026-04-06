import os
import logging
from pathlib import Path
from google.cloud import storage

logger = logging.getLogger("tracker.gcs")

def _get_client():
    """GCS ?대씪?댁뼵???앹꽦 (?몄쬆 ?ㅽ뙣 ??None 諛섑솚)"""
    try:
        return storage.Client()
    except Exception as e:
        logger.warning(f"GCS Client could not be initialized: {e}")
        return None

def upload_db(bucket_name: str, source_file: str, dest_name: str = "price_tracker.sqlite3"):
    """SQLite DB瑜?GCS濡??낅줈?쒗빀?덈떎."""
    if not bucket_name:
        return
    bucket_name = bucket_name.strip()  # ?욌뮘 怨듬갚 ?쒓굅 (Secret ?ㅼ엯??諛⑹?)
    try:
        storage_client = _get_client()
        if not storage_client:
            logger.error("Skipping GCS upload due to lack of credentials.")
            return
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(dest_name)
        blob.upload_from_filename(source_file)
        logger.info(f"DB uploaded to GCS: {bucket_name}/{dest_name}")
    except Exception as e:
        logger.error(f"GCS Upload failed: {e}")

def download_db(bucket_name: str, dest_file: str, source_name: str = "price_tracker.sqlite3"):
    """GCS?먯꽌 SQLite DB瑜??ㅼ슫濡쒕뱶?⑸땲??"""
    if not bucket_name:
        return False
    bucket_name = bucket_name.strip()  # ?욌뮘 怨듬갚 ?쒓굅 (Secret ?ㅼ엯??諛⑹?)
    try:
        storage_client = _get_client()
        if not storage_client:
            logger.error("Skipping GCS download due to lack of credentials.")
            return False
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_name)
        if blob.exists():
            blob.download_to_filename(dest_file)
            logger.info(f"DB downloaded from GCS: {bucket_name}/{source_name}")
            return True
        else:
            logger.info("No existing DB found in GCS. Starting fresh.")
            return False
    except Exception as e:
        logger.error(f"GCS Download failed: {e}")
        return False

