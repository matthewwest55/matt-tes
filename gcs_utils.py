import os
import urllib.parse
import urllib.request
import google.auth.transport.requests
from google.oauth2 import service_account


def read_gcs_file(
    bucket_name: str,
    file_path: str,
    key_file_path: str = None,
    as_text: bool = True,
    encoding: str = "utf-8",
) -> str | bytes:
    """Reads a file directly from a GCP Storage bucket using a service account key.

    Args:
        bucket_name: Name of the GCS bucket.
        file_path: Object path in the bucket (e.g., 'data/report.csv').
        key_file_path: Path to the service account JSON key. Defaults to
          GOOGLE_APPLICATION_CREDENTIALS env var if None.
        as_text: If True, returns a decoded string. If False, returns raw
          bytes.
        encoding: Character encoding for text mode (default 'utf-8').

    Returns:
        str | bytes: File contents.
    """
    # Fallback to environment variable if no path is explicitly provided
    key_file = key_file_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_file:
        raise ValueError(
            "Service account key path must be provided or set in GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )

    # 1. Obtain access token
    creds = service_account.Credentials.from_service_account_file(
        key_file,
        scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
    )
    creds.refresh(google.auth.transport.requests.Request())

    # 2. Encode GCS blob path
    encoded_file_path = urllib.parse.quote(file_path, safe="")

    # 3. Call REST API
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{encoded_file_path}?alt=media"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {creds.token}"}
    )

    with urllib.request.urlopen(req) as response:
        content = response.read()

    return content.decode(encoding) if as_text else content
