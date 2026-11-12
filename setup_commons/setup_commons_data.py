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

        # 1. Read optional project and patient metadata from manifest.tsv (columns 4 and 5)
        projects_raw = row[3].strip() if len(row) > 3 else "NA"
        patient_count_raw = row[4].strip() if len(row) > 4 else "NA"

        # Build optional metadata dict for Indexd record
        indexd_meta = {}
        if projects_raw and projects_raw.upper() != "NA":
            indexd_meta["projects"] = [p.strip() for p in projects_raw.split(";") if p.strip()]
        if patient_count_raw.isdigit():
            indexd_meta["patient_count"] = int(patient_count_raw)

        # Clean file path and build GCS URL
        clean_path = os.path.normpath(file_path).lstrip("./")
        file_name = os.path.basename(clean_path)
        gcs_url = f"{GCS_BUCKET_BASE.rstrip('/')}/{clean_path}"

        record_kwargs = {
            "file_name": file_name,
            "size": size_bytes,
            "hashes": {"md5": md5},
            "urls": [gcs_url],
            "acl": ["*"]
        }
        if indexd_meta:
            record_kwargs["metadata"] = indexd_meta

        # Register object in Indexd
        record = index_client.create_record(**record_kwargs)

        guid = record["did"]
        print(f"Indexed: {clean_path} | GUID: {guid}")

        # 2. Preserve metadata columns in indexed_records array (6 columns total)
        indexed_records.append([md5, size_bytes, file_path, guid, projects_raw, patient_count_raw])

# Export updated manifest containing generated GUIDs and full metadata
with open(INDEXED_MANIFEST, "w", newline="") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["md5", "size", "file_path", "guid", "projects", "patient_count"])
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

        projects_raw = (row.get("projects") or "").strip()
        patient_count_raw = (row.get("patient_count") or "").strip()

        ext = os.path.splitext(file_name)[1].lstrip(".").upper() or "UNKNOWN"

        gen3_discovery = {
            "file_name": file_name,
            "file_size": size_bytes,
            "md5sum": md5,
            "file_path": file_path,
            "data_format": ext,
            "project_id": PROJECT_ID
        }

        # 3. Add parsed projects and patient count to individual file MDS record
        if projects_raw and projects_raw.upper() != "NA":
            cleaned_proj = re.sub(r"[\[\]'\" ]", "", projects_raw)
            proj_list = [p.strip() for p in cleaned_proj.split(";") if p.strip()]
            if proj_list:
                gen3_discovery["projects"] = proj_list

        if patient_count_raw.isdigit():
            gen3_discovery["patient_count"] = int(patient_count_raw)

        metadata_payload = {
            "_guid_type": "file",
            "gen3_discovery": gen3_discovery
        }

        try:
            mds_client.create(
                guid=guid,
                metadata=metadata_payload,
                overwrite=True
            )
            print(f"Registered MDS metadata for GUID: {guid}")
        except Exception as e:
            print(f"Failed to post metadata for GUID {guid}: {e}")

print("\nMDS metadata ingestion complete.")

# 1. Group files by their parent subdirectory name and capture metadata
subdir_groups = defaultdict(list)

with open(INDEXED_MANIFEST, "r") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        file_path = row["file_path"].strip()
        norm_path = os.path.normpath(file_path)

        subdir_name = os.path.dirname(norm_path)
        if not subdir_name or subdir_name == ".":
            subdir_name = "root_files"

        item = {
            "object_id": row["guid"].strip(),
            "file_name": os.path.basename(file_path),
            "file_size": int(row["size"].strip()),
            "md5sum": row["md5"].strip()
        }

        # 4. Include projects and patient count in file manifest elements
        projects_raw = (row.get("projects") or "").strip()
        if projects_raw and projects_raw.upper() != "NA":
            cleaned_proj = re.sub(r"[\[\]'\" ]", "", projects_raw)
            proj_list = [p.strip() for p in cleaned_proj.split(";") if p.strip()]
            if proj_list:
                item["projects"] = proj_list

        patient_count_raw = (row.get("patient_count") or "").strip()
        if patient_count_raw.isdigit():
            item["patient_count"] = int(patient_count_raw)

        subdir_groups[subdir_name].append(item)

# 2. Process subdirectories and write output to both console and log file
success_count = 0

with open(LOG_FILE, "w") as log:
    def write_log(message):
        print(message)
        log.write(message + "\n")

    write_log(f"--- Starting Mesh PID Registration Run: {datetime.now().isoformat()} ---")

    for subdir_name, file_manifest in subdir_groups.items():
        clean_subdir_id = re.sub(r"[^a-zA-Z0-9_-]", "_", subdir_name)
        mesh_pid = f"{HOSTNAME}/mesh-{clean_subdir_id}"

        # 5. Aggregate projects and sum patient count for top-level Mesh PID metadata
        subdir_projects = set()
        subdir_patient_count = 0
        has_patient_count = False

        for file_item in file_manifest:
            if "projects" in file_item:
                subdir_projects.update(file_item["projects"])
            if "patient_count" in file_item:
                subdir_patient_count += file_item["patient_count"]
                has_patient_count = True

        gen3_discovery = {
            "study_name": f"Dataset - {subdir_name}",
            "study_id": subdir_name,
            "project_id": PROJECT_ID,
            "commons_name": HOSTNAME,
            "file_count": len(file_manifest),
            "manifest": file_manifest
        }

        proj_list = sorted(list(subdir_projects))
        if proj_list:
            gen3_discovery["projects"] = proj_list
        if has_patient_count:
            gen3_discovery["patient_count"] = subdir_patient_count

        mesh_payload = {
            "_guid_type": "discovery_metadata",
            "gen3_discovery": gen3_discovery
        }

        try:
            mds_client.create(guid=mesh_pid, metadata=mesh_payload, overwrite=True)
            write_log(
                f"SUCCESS | Mesh PID: {mesh_pid} | Subdirectory: '{subdir_name}' "
                f"| Files: {len(file_manifest)} | Projects: {proj_list or 'None'} | Patients: {subdir_patient_count if has_patient_count else 'None'}"
            )
            success_count += 1
        except Exception as e:
            write_log(f"ERROR   | Subdirectory: '{subdir_name}' | Reason: {e}")

    write_log("\n--- Execution Summary ---")
    write_log(f"Successfully created {success_count} Mesh PIDs across {len(subdir_groups)} subdirectories.")

print(f"\nExecution log written to: {os.path.abspath(LOG_FILE)}")
