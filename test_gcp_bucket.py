import requests
import time
from gcs_utils import read_gcs_file

TES_HOST = "http://localhost:8000/v1/tasks"
BUCKET = "tcga-test-bucket"
KEY_PATH = "gcp-key.json"

payload = {
    "name": "Write Math Result to GCS",
    "executors": [
        {
            "image": "alpine",
            "command": [
                "sh",
                "-c",
                "echo $((18 + 2)) > /tmp/result.txt"
            ]
        }
    ],
    "outputs": [
        {
            "path": "/tmp/result.txt",
            # Replace with your actual bucket and destination file path
            "url": f"gs://{BUCKET}/math-outputs/result.txt"
        }
    ]
}

res = requests.post(TES_HOST, json=payload)
task_id = res.json()["id"]
print("Submitted Task ID:", task_id)

task_status_url = f"{TES_HOST}/{task_id}?view=FULL"
status_res = requests.get(task_status_url)

while status_res.json()["state"] != "COMPLETE":
  print(f"STATUS: {status_res.json()['state']}")
  status_res = requests.get(task_status_url)
  time.sleep(1)


text_data = read_gcs_file(
    bucket_name=BUCKET, file_path="math-outputs/result.txt", key_file_path=KEY_PATH
)
print(text_data)
