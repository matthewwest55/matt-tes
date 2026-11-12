import requests
import os
import re
from collections import defaultdict
from gen3.auth import Gen3Auth
from gen3.metadata import Gen3Metadata

HUB_URL = "https://base.themattwest.com"
NUMBER_INSTANCES = 1
SOURCE_NODES = {}

# Starts at 0, which is what we want
for num in range(NUMBER_INSTANCES):
    SOURCE_NODES[f"node_{num}"] = f"https://data-instance-{num}.themattwest.com"

auth = Gen3Auth(HUB_URL, refresh_file="credentials.json")
hub_mds = Gen3Metadata(auth)

for node_name, node_url in SOURCE_NODES.items():
    print(f"Fetching metadata from {node_name}...")
    
    # CRITICAL: Append `data=True` to return full metadata dicts instead of GUID strings
    response = requests.get(f"{node_url}/mds/metadata?data=True&limit=5000", timeout=30)
    response.raise_for_status()
    remote_records = response.json()  # Returns: {"<guid>": {<metadata_blob>}}

    groups = defaultdict(list)
    for guid, data in remote_records.items():
        # Skip existing study-level GUIDs
        if data.get("_guid_type") == "discovery_metadata":
            continue

        # Extract subdirectory from metadata or parse file path if present
        file_path = data.get("file_path", "")
        subdir = data.get("subdir_name") or (os.path.dirname(file_path) if file_path else "default_collection")
        if not subdir or subdir == ".":
            subdir = "default_collection"

        groups[subdir].append({
            "object_id": guid,
            "file_name": data.get("file_name", os.path.basename(file_path) or "unknown"),
            "file_size": int(data.get("size", 0)),
            "md5sum": data.get("hashes", {}).get("md5") or data.get("md5sum", "")
        })

    print(f"Found {len(groups)} subdirectory groups for {node_name}.")

    print(groups)

    # Create dataset-level Mesh PIDs on the Hub
    for subdir, manifest in groups.items():
        clean_subdir = re.sub(r"[^a-zA-Z0-9_-]", "_", subdir)
        mesh_pid = f"hub/mesh-{node_name.lower()}-{clean_subdir}"
        payload = {
            "_guid_type": "discovery_metadata",
            "gen3_discovery": {
                "study_name": f"Dataset - {subdir}",
                "study_id": subdir,
                "source_commons": node_url,
                "file_count": len(manifest),
                "manifest": manifest
            }
        }
        
        hub_mds.create(guid=mesh_pid, metadata=payload, overwrite=True)
        print(f"Pushed {mesh_pid} with {len(manifest)} files.")
