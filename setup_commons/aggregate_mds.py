import requests
from collections import defaultdict
from gen3.auth import Gen3Auth
from gen3.metadata import Gen3Metadata

HUB_URL = "https://base.themattwest.com"
NUMBER_INSTANCES = 1
SOURCE_NODES = {}

# Starts at 0, which is what we want
for num in range(NUMBER_INSTANCES):
    SOURCE_NODES[num] = f"https://data-instance-{num}.themattwest.com"

# Authenticate against the Hub (requires an API key/credentials.json from Hub portal)
auth = Gen3Auth(HUB_URL, refresh_file="credentials.json")
hub_mds = Gen3Metadata(auth)

for node_name, node_url in SOURCE_NODES.items():
    print(f"Fetching metadata from {node_name}...")

    # 1. Fetch raw metadata or index records from remote node
    response = requests.get(f"{node_url}/mds/metadata?limit=5000", timeout=30)
    response.raise_for_status()
    remote_records = response.json()

    # 2. Group objects into subdirectories/projects
    groups = defaultdict(list)
    for guid, data in remote_records.items():
        # Skip existing study-level GUIDs if any
        if data.get("_guid_type") == "discovery_metadata":
            continue

        subdir = data.get("subdir_name", "default_collection")
        groups[subdir].append({
            "object_id": guid,
            "file_name": data.get("file_name", "unknown"),
            "file_size": data.get("size", 0),
            "md5sum": data.get("hashes", {}).get("md5", "")
        })

    # 3. Create and push dataset-level Mesh PIDs directly to the Hub
    for subdir, manifest in groups.items():
        mesh_pid = f"hub/mesh-{node_name.lower()}-{subdir}"
        payload = {
            "_guid_type": "discovery_metadata",
            "gen3_discovery": {
                "study_name": f"{node_name} - {subdir}",
                "study_id": f"{node_name}_{subdir}",
                "source_commons": node_url,
                "file_count": len(manifest),
                "manifest": manifest
            }
        }
        
        hub_mds.create(guid=mesh_pid, metadata=payload, overwrite=True)
        print(f"Pushed {mesh_pid} to Hub with {len(manifest)} files.")