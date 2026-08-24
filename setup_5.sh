git clone https://github.com/matthewwest55/matt-tes.git
cd matt-tes

mv ../extra/manifest.tsv .
mv ../extra/gcp-key.json .

# Wait for services to be running
SERVICES=(
    "user"
    "index"
)

HOSTNAME="base"

for service in "${SERVICES[@]}"; do
    # Pass your endpoint URL as an argument, or replace the default below
    ENDPOINT="https://${HOSTNAME}.themattwest.com/${service}/_status"

    echo "Waiting for $ENDPOINT to report healthy status..."

    until curl -s "$ENDPOINT" | grep -qi "Healthy"; do
        sleep 1
    done

    echo "${ENDPOINT} is up and healthy!"
done

# do poetry install
/home/$(whoami)/.local/bin/poetry lock
/home/$(whoami)/.local/bin/poetry install

# Start by getting the credentials.json file
./get_credentials_file.sh

# change "base" to the echo hostname command
poetry run python setup_commons_data.py "base"
