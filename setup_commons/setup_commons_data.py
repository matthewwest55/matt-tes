from collections import defaultdict
from datetime import datetime
import re
import csv
import os
import sys
from gen3.auth import Gen3Auth
from gen3.index import Gen3Index
from gen3.metadata import Gen3Metadata

# Configuration
HOSTNAME = sys.argv[1]
GEN3_ENDPOINT = f"https://{HOSTNAME}.themattwest.com"
CREDENTIALS_FILE = "credentials.json"
MANIFEST_FILE = "manifest.tsv"
GCS_BUCKET_BASE = "gs://data-instance-0-test-bucket"  # Base GCS bucket path
INDEXED_MANIFEST = "indexed_manifest.tsv"
PROJECT_ID = "demo-test"
LOG_FILE = "mesh_pid_registration.log"


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
with open(INDEXED_MANIFEST, "w", newline="") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["md5", "size", "file_path", "guid"])
    writer.writerows(indexed_records)

print(f"\nSuccessfully indexed all files! Output saved to {INDEXED_MANIFEST}")

# Authenticate with Gen3
mds_client = Gen3Metadata(auth)

# Read the indexed manifest and post metadata for each GUID
with open(INDEXED_MANIFEST, "r") as f:
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

# 1. Group files by their parent subdirectory name
subdir_groups = defaultdict(list)

with open(INDEXED_MANIFEST, "r") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        file_path = row["file_path"].strip()
        norm_path = os.path.normpath(file_path)

        # Extracts top subdirectory (e.g., "./subdir_001/file.fastq" -> "subdir_001")
        subdir_name = os.path.dirname(norm_path)
        if not subdir_name or subdir_name == ".":
            subdir_name = "root_files"

        subdir_groups[subdir_name].append({
            "object_id": row["guid"].strip(),
            "file_name": os.path.basename(file_path),
            "file_size": int(row["size"].strip()),
            "md5sum": row["md5"].strip()
        })

# 2. Process subdirectories and write output to both console and log file

success_count = 0

with open(LOG_FILE, "w") as log:
    def write_log(message):
        print(message)
        log.write(message + "\n")

    write_log(f"--- Starting Mesh PID Registration Run: {datetime.now().isoformat()} ---")

    for subdir_name, file_manifest in subdir_groups.items():
        # Sanitize subdirectory name into a valid PID identifier string
        clean_subdir_id = re.sub(r"[^a-zA-Z0-9_-]", "_", subdir_name)
        mesh_pid = f"{HOSTNAME}/mesh-{clean_subdir_id}"

        # Construct study-level metadata for this specific subdirectory
        mesh_payload = {
            "_guid_type": "discovery_metadata",
            "gen3_discovery": {
                "study_name": f"Dataset - {subdir_name}",
                "site_id": subdir_name,
                "project_id": PROJECT_ID,
                "commons_id": HOSTNAME,
                "file_count": len(file_manifest),
                "manifest": file_manifest  # Contains only the files in this subdirectory
            }
        }

        try:
            mds_client.create(guid=mesh_pid, metadata=mesh_payload, overwrite=True)
            write_log(f"SUCCESS | Mesh PID: {mesh_pid} | Subdirectory: '{subdir_name}' | Files: {len(file_manifest)}")
            success_count += 1
        except Exception as e:
            write_log(f"ERROR   | Subdirectory: '{subdir_name}' | Reason: {e}")

    write_log("\n--- Execution Summary ---")
    write_log(f"Successfully created {success_count} Mesh PIDs across {len(subdir_groups)} subdirectories.")

print(f"\nExecution log written to: {os.path.abspath(LOG_FILE)}")
