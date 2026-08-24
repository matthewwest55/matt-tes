from gen3.auth import Gen3Auth
from gen3.metadata import Gen3Metadata

auth = Gen3Auth(endpoint="https://base.themattwest.com", refresh_file="credentials.json")
mds = Gen3Metadata(auth)

# Query by specific fields (e.g., format and project)
query_str = "gen3_discovery.project_id=demo-test"
results = mds.query(query=query_str, return_full_metadata=True, limit=1000)

for guid, data in results.items():
    print(guid)
    print(data)
    file_info = data["gen3_discovery"]
    print(f"Found GUID: {guid} | File: {file_info['file_name']} | Size: {file_info['file_size']} bytes")
