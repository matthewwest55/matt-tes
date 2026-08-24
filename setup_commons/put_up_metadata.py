import csv
import os
import sys
from gen3.auth import Gen3Auth
from gen3.metadata import Gen3Metadata

# Configuration
GEN3_ENDPOINT = f"https://{sys.argv[1]}.themattwest.com"
CREDENTIALS_FILE = "credentials.json"
MANIFEST_FILE = "indexed_manifest.tsv"
PROJECT_ID = "demo-test"

# Authenticate with Gen3
auth = Gen3Auth(endpoint=GEN3_ENDPOINT, refresh_file=CREDENTIALS_FILE)
mds_client = Gen3Metadata(auth)

# Read the indexed manifest and post metadata for each GUID
with open(MANIFEST_FILE, "r") as f:
    reader = csv.DictReader(f, delimiter="\t")
    
    for row in reader:
        guid = row["guid"].strip()
        md5 = row["md5"].strip()
        size_bytes = int(row["size"].strip())
        file_path = row["file_path"].strip()
        file_name = os.path.basename(file_path)
        
        # Determine basic file format extension
        ext = os.path.splitext(file_name)[1].lstrip(".").upper() or "UNKNOWN"

        # Construct the MDS payload (gen3_discovery block powers the UI Discovery page)
        metadata_payload = {
            "_guid_type": "file",
            "gen3_discovery": {
                "file_name": file_name,
                "file_size": size_bytes,
                "md5sum": md5,
                "file_path": file_path,
                "data_format": ext,
                "project_id": PROJECT_ID
            }
        }

        try:
            # Register or overwrite the metadata object on the GUID
            mds_client.create(
                guid=guid,
                metadata=metadata_payload,
                overwrite=True
            )
            print(f"Registered MDS metadata for GUID: {guid}")
        except Exception as e:
            print(f"Failed to post metadata for GUID {guid}: {e}")

print("\nMDS metadata ingestion complete.")
