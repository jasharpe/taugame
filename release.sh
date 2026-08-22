#!/bin/bash
# Build the container, check it works, and roll it out to GCP.
#
#   ./release.sh              build, smoke test, push to GCR, cycle the group
#   ./release.sh --dry_run    build and smoke test only; pushes nothing
#   ./release.sh --serve      build, smoke test, then leave it running for manual checks
#
# The smoke test runs in every mode, so a broken container is never pushed. It
# mirrors production as closely as it can locally: the container is started with
# the same command the instance template uses (python ./tau.py, no arguments, so
# port 80 and ssl_port 443), and pointed at a real MySQL rather than SQLite,
# because production runs MySQL and its stricter sql_mode rejects queries SQLite
# happily accepts.
#
# Docker Desktop is not needed. Colima supplies the docker daemon, and this
# script starts it if it is not already up. If the script started it, it is
# stopped again on the way out (including on failure); if it was already
# running it is left alone.
set -euo pipefail

PROJECT=tau-game
IMAGE=gcr.io/$PROJECT/websockettau
ZONE=us-central1-a
GROUP=tau-game-ig
# The GCE instances are x86_64 while this Mac is arm64, so the image has to
# be cross-built. An arm64 image pushed to GCR starts and dies immediately
# with "exec format error", which takes the site down.
PLATFORM=linux/amd64
EXPECTED_ARCH=amd64

# Ports for the smoke test and --serve. Deliberately not 8000/8001 so a
# development server can keep running alongside.
HTTP_PORT=8400
HTTPS_PORT=8401

NETWORK=tau-release-net
MYSQL_NAME=tau-release-mysql
MYSQL_PASSWORD=smoketest
MYSQL_DB=tau_game
# Cloud SQL runs MySQL 5.7, whose default sql_mode this pins, so the test does
# not drift if the local mysql image changes its defaults.
MYSQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'

usage() {
  echo "usage: $0 [--dry_run|--serve]" >&2
  exit 2
}

MODE=deploy
case "${1:-}" in
  "")        ;;
  --dry_run) MODE=dry_run; shift ;;
  --serve)   MODE=serve;   shift ;;
  *)         usage ;;
esac
[ $# -eq 0 ] || usage

if ! command -v colima >/dev/null 2>&1; then
  echo "colima is not installed. Run: brew install colima docker" >&2
  exit 1
fi

# Check push credentials before the slow build rather than after it. "gcloud
# auth login" authenticates the gcloud CLI only; docker keeps its own
# credential store, and without a helper wired up the push fails late with
# "Unauthenticated request".
if [ "$MODE" = "deploy" ]; then
  if ! command -v docker-credential-gcloud >/dev/null 2>&1; then
    echo "docker-credential-gcloud is not on PATH; it ships with the gcloud SDK." >&2
    echo "Run: gcloud auth configure-docker" >&2
    exit 1
  fi
  if ! grep -q '"gcr\.io"' "$HOME/.docker/config.json" 2>/dev/null; then
    echo "docker has no credential helper for gcr.io, so the push would fail with" >&2
    echo "\"Unauthenticated request\" even after a successful gcloud auth login." >&2
    echo "Run: gcloud auth configure-docker" >&2
    exit 1
  fi
fi

started_colima=0
container=""
cookie_jar=""
started_support=0

cleanup() {
  status=$?
  [ -n "$cookie_jar" ] && rm -f "$cookie_jar"
  if [ -n "$container" ]; then
    docker rm -f "$container" >/dev/null 2>&1 || true
  fi
  if [ "$started_support" = "1" ]; then
    docker rm -f "$MYSQL_NAME" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
  fi
  if [ "$started_colima" = "1" ]; then
    echo "==> Stopping colima"
    colima stop || true
  fi
  exit $status
}
trap cleanup EXIT
# Turn Ctrl-C into a normal exit so the cleanup above runs exactly once.
trap 'exit 130' INT TERM

mysql_do() {
  # Keep real errors visible; drop only mysql's password-on-the-command-line
  # warning. Swallowing all of stderr here hides schema problems completely.
  local out
  if ! out=$(docker exec -i "$MYSQL_NAME" mysql -uroot -p"$MYSQL_PASSWORD" "$@" 2>&1); then
    echo "$out" | grep -v 'Using a password on the command line' >&2 || true
    return 1
  fi
  echo "$out" | grep -v 'Using a password on the command line' || true
}

# Fetch a path and require one of the given status codes.
expect() {
  path=$1; shift
  code=$(curl -sk -o /dev/null -b "$cookie_jar" -c "$cookie_jar" \
              -w '%{http_code}' "https://localhost:$HTTPS_PORT$path")
  for want in "$@"; do
    if [ "$code" = "$want" ]; then
      printf '    %-30s %s\n' "$path" "$code"
      return 0
    fi
  done
  echo "    FAILED: $path returned $code, wanted one of: $*" >&2
  docker logs "$container" 2>&1 | tail -40 >&2 || true
  exit 1
}

start_support() {
  echo "==> Starting MySQL (production uses Cloud SQL MySQL 5.7, not SQLite)"
  # Remove attached containers before the network, otherwise the network
  # removal fails and the create below reports that it already exists.
  docker rm -f "$MYSQL_NAME" tau-release-app >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  docker network create "$NETWORK" >/dev/null
  started_support=1
  docker run -d --name "$MYSQL_NAME" --network "$NETWORK" \
    -e MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD" -e MYSQL_DATABASE="$MYSQL_DB" \
    mysql:8 --sql-mode="$MYSQL_MODE" >/dev/null

  for _ in $(seq 1 120); do
    if docker exec "$MYSQL_NAME" mysqladmin ping -uroot -p"$MYSQL_PASSWORD" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "    FAILED: MySQL never became ready" >&2
  docker logs "$MYSQL_NAME" 2>&1 | tail -20 >&2 || true
  exit 1
}

# The leaderboard aggregates are only exercised once scores exist, so put a
# couple of rows in. Without this the queries short-circuit on an empty table
# and a query MySQL would reject never runs.
seed_scores() {
  mysql_do "$MYSQL_DB" <<'SQL'
INSERT INTO players (id, name) VALUES (1, 'smoketest');
INSERT INTO teams (id) VALUES (1);
INSERT INTO team_players (team_id, player_id) VALUES (1, 1);
INSERT INTO games (id, game_type, deck_json, seed) VALUES (1, '3tau', '[]', 1), (2, '3tau', '[]', 2);
INSERT INTO scores (id, elapsed_time, num_players, game_id, team_id, game_type, date, player_scores_json, invalid)
VALUES (1, 12.5, 1, 1, 1, '3tau', UTC_TIMESTAMP(), '{"smoketest": 3}', 0),
       (2, 34.5, 1, 2, 1, '3tau', UTC_TIMESTAMP(), '{"smoketest": 4}', 0);
INSERT INTO score_players (score_id, player_id) VALUES (1, 1), (2, 1);
-- A score with no states would make the recap page divide by zero, and it
-- would not exercise the board reconstruction either. These cards are a real
-- 3 Tau: the last coordinate runs 0,1,2 and the rest match.
INSERT INTO states (id, elapsed_time, board_json, cards_json, game_id, player_id) VALUES
  (1, 12.5,
   '[[0,0,0,0],[0,0,0,1],[0,0,0,2],[0,0,1,0],[0,0,1,1],[0,0,1,2],[0,0,2,0],[0,0,2,1],[0,0,2,2],[0,1,0,0],[0,1,0,1],[0,1,0,2]]',
   '[[0,0,0,0],[0,0,0,1],[0,0,0,2]]', 1, 1),
  (2, 34.5,
   '[[0,0,0,0],[0,0,0,1],[0,0,0,2],[0,0,1,0],[0,0,1,1],[0,0,1,2],[0,0,2,0],[0,0,2,1],[0,0,2,2],[0,1,0,0],[0,1,0,1],[0,1,0,2]]',
   '[[0,0,1,0],[0,0,1,1],[0,0,1,2]]', 2, 1);
-- A score whose player_scores_json is missing a player that is on the score.
-- Rows shaped like this exist in production: MySQL compares names
-- case-insensitively, so before the save_game fix a player whose cookie read
-- "Legacy" could be stored as "legacy" and the counts keyed by the other
-- spelling. The leaderboard must render these rather than raising KeyError.
INSERT INTO players (id, name) VALUES (2, 'legacy');
INSERT INTO teams (id) VALUES (2);
INSERT INTO team_players (team_id, player_id) VALUES (2, 2);
INSERT INTO games (id, game_type, deck_json, seed) VALUES (3, '3tau', '[]', 3);
INSERT INTO scores (id, elapsed_time, num_players, game_id, team_id, game_type, date, player_scores_json, invalid)
VALUES (3, 5.5, 1, 3, 2, '3tau', UTC_TIMESTAMP(), '{"Legacy": 5}', 0);
INSERT INTO score_players (score_id, player_id) VALUES (3, 2);
INSERT INTO states (id, elapsed_time, board_json, cards_json, game_id, player_id) VALUES
  (3, 5.5,
   '[[0,0,0,0],[0,0,0,1],[0,0,0,2],[0,0,1,0],[0,0,1,1],[0,0,1,2],[0,0,2,0],[0,0,2,1],[0,0,2,2],[0,1,0,0],[0,1,0,1],[0,1,0,2]]',
   '[[0,0,2,0],[0,0,2,1],[0,0,2,2]]', 3, 2);
SQL
}

smoke_test() {
  start_support

  echo "==> Smoke testing with the production command line, on port $HTTPS_PORT"
  # The instance template overrides the Dockerfile ENTRYPOINT with
  # command: [python] / args: [./tau.py], so no --debug and the argparse
  # defaults of port 80 / ssl_port 443. Match that exactly.
  # Run the same architecture that will be deployed. On this Mac that means
  # qemu emulation, which is slower to start but exercises the real artefact.
  container=$(docker run -d --name tau-release-app --network "$NETWORK" \
    --platform "$PLATFORM" \
    -e db=mysql -e mysql_password="$MYSQL_PASSWORD" \
    -e mysql_addr="$MYSQL_NAME:3306" -e db_name="$MYSQL_DB" \
    -p "$HTTP_PORT:80" -p "$HTTPS_PORT:443" \
    --entrypoint python "$IMAGE" ./tau.py)
  cookie_jar=$(mktemp)

  ready=0
  for _ in $(seq 1 120); do
    if curl -sk -o /dev/null "https://localhost:$HTTPS_PORT/"; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" != "1" ]; then
    echo "    FAILED: container never started serving on 443" >&2
    docker logs "$container" 2>&1 | tail -40 >&2 || true
    exit 1
  fi

  # The app creates its schema lazily, on the first request that actually
  # touches the database. Serving "/" only redirects, so force a real query
  # first and then wait for the tables to appear before seeding.
  curl -sk -o /dev/null "https://localhost:$HTTPS_PORT/leaderboard/alltime" || true
  schema=0
  for _ in $(seq 1 30); do
    if mysql_do -N -e "SELECT COUNT(*) FROM information_schema.tables \
         WHERE table_schema='$MYSQL_DB' AND table_name='scores'" | grep -q '1'; then
      schema=1; break
    fi
    sleep 1
  done
  if [ "$schema" != "1" ]; then
    echo "    FAILED: the app never created its schema in MySQL" >&2
    docker logs "$container" 2>&1 | tail -40 >&2 || true
    exit 1
  fi

  if ! seed_scores; then
    echo "    FAILED: could not seed scores into MySQL" >&2
    exit 1
  fi

  expect /choose_name 200
  name_code=$(curl -sk -o /dev/null -b "$cookie_jar" -c "$cookie_jar" \
                   -d 'name=smoketest' -w '%{http_code}' \
                   "https://localhost:$HTTPS_PORT/choose_name")
  if [ "$name_code" != "302" ]; then
    echo "    FAILED: could not set a name (got $name_code)" >&2
    exit 1
  fi
  printf '    %-30s %s\n' "POST /choose_name" "$name_code"

  expect / 200
  expect /about 200
  expect /settings 200
  expect /static/tau.js 200
  expect /static/styles.css 200

  # These run the aggregate queries that MySQL's ONLY_FULL_GROUP_BY polices.
  expect /leaderboard/alltime 200
  expect /leaderboard/players/alltime 200
  expect /leaderboard/games/alltime 200
  expect /leaderboard/alltime/smoketest 200
  expect /leaderboard/games/alltime/smoketest 200
  expect /graph/smoketest 200
  expect /recap/1 200

  # Creating and opening a game exercises the lobby and the game template.
  game_url=$(curl -sk -o /dev/null -b "$cookie_jar" -c "$cookie_jar" -X POST \
                  -w '%{redirect_url}' "https://localhost:$HTTPS_PORT/new_game/r4tau")
  if [ -z "$game_url" ]; then
    echo "    FAILED: creating a game did not redirect" >&2
    exit 1
  fi
  game_code=$(curl -sk -o /dev/null -b "$cookie_jar" -w '%{http_code}' "$game_url")
  if [ "$game_code" != "200" ]; then
    echo "    FAILED: $game_url returned $game_code" >&2
    docker logs "$container" 2>&1 | tail -40 >&2 || true
    exit 1
  fi
  printf '    %-30s %s\n' "new game + game page" "$game_code"

  if docker logs "$container" 2>&1 | grep -qiE 'traceback|exception'; then
    echo "    FAILED: errors in the container log" >&2
    docker logs "$container" 2>&1 | tail -40 >&2
    exit 1
  fi

  # Report the same figure "docker images" shows. Note that docker image
  # inspect .Size reports the compressed size instead, which is much smaller.
  size=$(docker images "$IMAGE" --format '{{.Size}}' | head -1)
  echo "    all checks passed (${size} unpacked)"
}

if colima status >/dev/null 2>&1; then
  echo "==> colima already running; leaving it up afterwards"
else
  echo "==> Starting colima"
  colima start
  started_colima=1
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required to build for $PLATFORM." >&2
  echo "Run: brew install docker-buildx, then add" >&2
  echo "  \"cliPluginsExtraDirs\": [\"/opt/homebrew/lib/docker/cli-plugins\"]" >&2
  echo "to ~/.docker/config.json" >&2
  exit 1
fi

echo "==> Building $IMAGE for $PLATFORM"
docker buildx build --platform "$PLATFORM" --load -t "$IMAGE" .

# Never let a wrong-architecture image get as far as the push.
built_arch=$(docker image inspect "$IMAGE" --format '{{.Architecture}}' 2>/dev/null || echo unknown)
if [ "$built_arch" != "$EXPECTED_ARCH" ]; then
  echo "FAILED: built image is '$built_arch' but the instances need '$EXPECTED_ARCH'." >&2
  echo "An image of the wrong architecture will crash-loop with \"exec format error\"." >&2
  exit 1
fi
echo "==> Architecture verified: $built_arch"

smoke_test

case "$MODE" in
  serve)
    echo "==> Container is running for manual checks:"
    echo ""
    echo "      https://localhost:$HTTPS_PORT/"
    echo ""
    echo "    It is running the production command against a throwaway MySQL,"
    echo "    seeded with one player and two scores."
    echo "    The certificate is self-signed, so accept the browser warning once."
    echo "    Use the https URL directly: the container only knows its own"
    echo "    internal port, so its http->https redirect will not point here."
    echo "    Following the container log; press Ctrl-C to stop and clean up."
    echo ""
    docker logs -f "$container"
    ;;
  dry_run)
    echo "==> Dry run complete. Nothing was pushed and the group was untouched."
    ;;
  deploy)
    docker rm -f "$container" >/dev/null; container=""
    echo "==> Pushing $IMAGE"
    docker push "$IMAGE"
    # Cycle the managed instance group so it picks up the image just pushed.
    # "replace" recreates the VMs, which guarantees a cold docker cache and so
    # a genuine re-pull of the :latest tag. "rolling-action restart" is the
    # lighter equivalent of the old instances-reset, but it keeps the boot disk
    # and can therefore reuse a cached image with the same tag.
    echo "==> Cycling $GROUP"
    gcloud compute instance-groups managed rolling-action replace "$GROUP" \
      --project="$PROJECT" --zone="$ZONE" --max-unavailable=1

    echo "==> Waiting for the group to become stable"
    gcloud compute instance-groups managed wait-until "$GROUP" --stable \
      --project="$PROJECT" --zone="$ZONE"
    echo "==> Released."
    ;;
esac
