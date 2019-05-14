docker build -t gcr.io/tau-game/websockettau . && \
  docker push gcr.io/tau-game/websockettau && \
  gcloud compute instances reset --project=tau-game --zone=us-central1-c tau-game-1
