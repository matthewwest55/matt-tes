from gen3.auth import Gen3Auth
from gen3.file import Gen3File

auth = Gen3Auth(endpoint="https://base.themattwest.com", refresh_file="credentials.json")
file_tool = Gen3File(auth)

file_tool.download_single("PREFIX/4c2c044f-8a95-4f9b-89fe-6357693243a2", "./")
