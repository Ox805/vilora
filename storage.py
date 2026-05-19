"""File storage using Google Cloud Storage."""
import os
import sys
import json
from datetime import timedelta


def _get_client():
    """Get GCS client, or None if not configured."""
    creds_json = os.environ.get('GCS_CREDENTIALS_JSON')
    if not creds_json:
        return None
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_data)
        return storage.Client(credentials=credentials)
    except ImportError:
        sys.stderr.write("[Vilora] google-cloud-storage not installed.\n")
        return None
    except Exception as e:
        sys.stderr.write(f"[Vilora] GCS client error: {e}\n")
        return None


def _get_bucket():
    """Get the configured GCS bucket."""
    client = _get_client()
    if not client:
        return None
    bucket_name = os.environ.get('GCS_BUCKET_NAME', 'vilora-uploads')
    return client.bucket(bucket_name)


def upload_file(session_id, file_obj, filename, content_type):
    """Upload a file to GCS. Returns the blob path or None on failure.

    Files are stored as: sessions/{session_id}/{uuid}_{filename}
    """
    import uuid
    bucket = _get_bucket()
    if not bucket:
        sys.stderr.write(f"[Vilora] GCS not configured. File upload skipped: {filename}\n")
        return None

    safe_filename = filename.replace('/', '_').replace('\\', '_')
    blob_path = f"sessions/{session_id}/{uuid.uuid4().hex}_{safe_filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_file(file_obj, content_type=content_type)
    sys.stderr.write(f"[Vilora] File uploaded: {blob_path}\n")
    return blob_path


def get_download_url(blob_path, expiry_minutes=60, inline=False, content_type=None):
    """Generate a signed URL for downloading or viewing a file."""
    bucket = _get_bucket()
    if not bucket:
        return None
    blob = bucket.blob(blob_path)
    kwargs = {
        'expiration': timedelta(minutes=expiry_minutes),
        'method': 'GET',
    }
    if inline:
        kwargs['response_disposition'] = 'inline'
        if content_type:
            kwargs['response_type'] = content_type
    else:
        kwargs['response_disposition'] = 'attachment'
    url = blob.generate_signed_url(**kwargs)
    return url


def delete_file(blob_path):
    """Delete a file from GCS."""
    bucket = _get_bucket()
    if not bucket:
        return False
    blob = bucket.blob(blob_path)
    try:
        blob.delete()
        return True
    except Exception as e:
        sys.stderr.write(f"[Vilora] File delete error: {e}\n")
        return False


def read_bytes(blob_path):
    """Fetch the raw bytes of a stored file. Returns None on failure."""
    bucket = _get_bucket()
    if not bucket:
        return None
    blob = bucket.blob(blob_path)
    try:
        return blob.download_as_bytes()
    except Exception as e:
        sys.stderr.write(f"[Vilora] File read error ({blob_path}): {e}\n")
        return None
