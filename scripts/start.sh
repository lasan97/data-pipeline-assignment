set -eu

python -m src.reset_db
python -m src.event_store --sessions "${EVENT_SESSIONS:-500}" --seed "${EVENT_SEED:-1}"
python -m src.dashboard --host 0.0.0.0 --port "${DASHBOARD_PORT:-8050}"
