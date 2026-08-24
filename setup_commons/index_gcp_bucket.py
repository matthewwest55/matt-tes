import csv
import os
import sys
from gen3.auth import Gen3Auth
from gen3.index import Gen3Index

# Configuration
GEN3_ENDPOINT = f"https://{sys.argv[1]}.themattwest.com"
CREDENTIALS_FILE = "credentials.json"
MANIFEST_FILE = "manifest.tsv"
GCS_BUCKET_BASE = "gs://data-instance-0-test-bucket"  # Base GCS bucket path
OUTPUT_MANIFEST = "indexed_manifest.tsv"

# Authenticate with Gen3
auth = Gen3Auth(endpoint=GEN3_ENDPOINT, refresh_file=CREDENTIALS_FILE)
index_client = Gen3Index(auth)

indexed_records = []

# Process and index files from manifest.tsv
with open(MANIFEST_FILE, "r") as f:
    reader = csv.reader(f, delimiter="\t")
    for row in reader:
        if not row or len(row) < 3:
            continue

        md5, size_bytes, file_path = row[0].strip(), int(row[1].strip()), row[2].strip()

        # Clean file path and build GCS URL
        # e.g., converts "./folder1/sample.fastq" -> "gs://your-gen3-bucket-name/folder1/sample.fastq"
        clean_path = os.path.normpath(file_path).lstrip("./")
        file_name = os.path.basename(clean_path)
        gcs_url = f"{GCS_BUCKET_BASE.rstrip('/')}/{clean_path}"

        # Register object in Indexd
        record = index_client.create_record(
            file_name=file_name,
            size=size_bytes,
            hashes={"md5": md5},
            urls=[gcs_url],
            acl=["*"]  # Replace with specific ACLs if required, e.g. ["programs.demo-projects.test"]
        )

        guid = record["did"]
        print(f"Indexed: {clean_path} | GUID: {guid}")

        # Save record mapping for metadata creation step
        indexed_records.append([md5, size_bytes, file_path, guid])

# Export updated manifest containing the generated GUIDs
with open(OUTPUT_MANIFEST, "w", newline="") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["md5", "size", "file_path", "guid"])
    writer.writerows(indexed_records)

print(f"\nSuccessfully indexed all files! Output saved to {OUTPUT_MANIFEST}")
