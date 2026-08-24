import json
import subprocess
import requests

# Configuration
COMMONS_DOMAIN = "https://base.themattwest.com"  # Replace with your domain
USERNAME = "test"
OUTPUT_FILE = "credentials.json"

# Step 1: Execute kubectl to retrieve the access_token
kubectl_cmd = (
    "kubectl exec -c fence "
    "$(kubectl get pods | grep '^fence-deployment' | awk '{print $1}') -- "
    f"fence-create token-create --scopes openid,user,fence,data,credentials,google_service_account "
    f"--type access_token --exp 3600 --username {USERNAME} | tail -1"
)

print("Fetching temporary access token via kubectl...")
try:
    result = subprocess.run(
        kubectl_cmd, shell=True, capture_output=True, text=True, check=True
    )
    access_token = result.stdout.strip()
    if not access_token:
        raise ValueError("Access token output was empty.")
except Exception as e:
    print(f"Failed to fetch access token: {e}")
    exit(1)

# Step 2: Request CDIS credentials from the Fence API
endpoint = f"{COMMONS_DOMAIN.rstrip('/')}/user/credentials/cdis/"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}

print(f"Requesting CDIS API key from {endpoint}...")
response = requests.post(endpoint, headers=headers)

# Step 3: Parse and save response to credentials.json
if response.status_code in (200, 201):
    credentials_data = response.json()
    with open(OUTPUT_FILE, "w") as f:
        json.dump(credentials_data, f, indent=2)
    print(f"Successfully generated and saved credentials to '{OUTPUT_FILE}'")
else:
    print(f"API Request Failed [{response.status_code}]: {response.text}")
