import requests
import time
from gcs_utils import read_gcs_file

TES_HOST = "http://localhost:8000/v1/tasks"
BUCKET = "tcga-test-bucket"
KEY_PATH = "gcp-key.json"

import time
import requests


def build_payload(name, command_str, output_path, gcs_rel_path, image="alpine"):
    """Generates a standardized TES task payload."""
    return {
        "name": name,
        "executors": [
            {
                "image": image,
                "command": ["sh", "-c", command_str],
            }
        ],
        "outputs": [
            {
                "path": output_path,
                "url": f"gs://{BUCKET}/{gcs_rel_path}",
            }
        ],
    }


def execute_tes_task(payload, gcs_rel_path=None):
    """Submits payload, polls status until finished, and fetches output from GCS."""
    res = requests.post(TES_HOST, json=payload)
    res.raise_for_status()
    task_id = res.json()["id"]
    print(f"\n['{payload['name']}'] Submitted Task ID: {task_id}")

    task_status_url = f"{TES_HOST}/{task_id}?view=FULL"

    while True:
        status_res = requests.get(task_status_url).json()
        state = status_res.get("state")
        print(f"['{payload['name']}'] STATUS: {state}")

        if state == "COMPLETE":
            break
        elif state in ["EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED"]:
            print(f"['{payload['name']}'] Task failed with state: {state}")
            return None

        time.sleep(1)

    if gcs_rel_path:
        text_data = read_gcs_file(
            bucket_name=BUCKET, file_path=gcs_rel_path, key_file_path=KEY_PATH
        )
        print(f"Output: {text_data.strip()}")
        return text_data


# --- Usage Example ---

# 1. Define task parameters cleanly in a list
task_definitions = [
    {
        "name": "Sum Task 1 (10 + 20)",
        "cmd": "echo $((10 + 20)) > /tmp/res1.txt",
        "out": "/tmp/res1.txt",
        "gcs": "math-outputs/res1.txt",
    },
    {
        "name": "Sum Task 2 (30 + 40)",
        "cmd": "echo $((30 + 40)) > /tmp/res2.txt",
        "out": "/tmp/res2.txt",
        "gcs": "math-outputs/res2.txt",
    },
    {
        "name": "Sum Task 3 (50 + 60)",
        "cmd": "echo $((50 + 60)) > /tmp/res3.txt",
        "out": "/tmp/res3.txt",
        "gcs": "math-outputs/res3.txt",
    },
]

# 2. Loop through and execute each task
total_sum = 0
for t in task_definitions:
    payload = build_payload(t["name"], t["cmd"], t["out"], t["gcs"])
    result_text = execute_tes_task(payload, gcs_rel_path=t["gcs"])

    if result_text is not None:
        total_sum += int(result_text)

# 3. Print final aggregated sum
print("\n" + "=" * 40)
print(f"Final Aggregated Sum: {total_sum}")
print("=" * 40)
