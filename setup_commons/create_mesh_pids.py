from collections import defaultdict
import csv
from datetime import datetime
import os
import re
import sys
from gen3.auth import Gen3Auth
from gen3.metadata import Gen3Metadata

# Configuration
HOSTNAME = sys.argv[1]
GEN3_ENDPOINT = f"https://{HOSTNAME}.themattwest.com"
CREDENTIALS_FILE = "credentials.json"
INDEXED_MANIFEST = "setup_commons/indexed_manifest.tsv"
PROJECT_ID = "demo-test"
LOG_FILE = "setup_commons/mesh_pid_registration.log"

# Authenticate with Gen3
auth = Gen3Auth(endpoint=GEN3_ENDPOINT, refresh_file=CREDENTIALS_FILE)
mds_client = Gen3Metadata(auth)

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
                "study_id": subdir_name,
                "project_id": PROJECT_ID,
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
