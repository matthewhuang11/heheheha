#!/usr/bin/env bash
# Spins each side on its own so you can check wiring and direction.
# Put the robot on a box with the wheels in the air first.
# Usage: tools/motor_test.sh [pi-ip]
PI="${1:-172.20.10.11}"

run() {  # run <label> <throttle> <turn> <seconds>
  echo ">> $1"
  end=$((SECONDS + $4))
  while [ $SECONDS -lt $end ]; do
    curl -s -X POST -H 'Content-Type: application/json' \
      -d "{\"throttle\":$2,\"turn\":$3}" "http://$PI:8000/api/drive" >/dev/null
    sleep 0.15
  done
  curl -s -X POST "http://$PI:8000/api/stop" >/dev/null
  sleep 1
}

# throttle + turn = left side, throttle - turn = right side
run "LEFT wheels forward"   0.5  0.5 2
run "LEFT wheels backward" -0.5 -0.5 2
run "RIGHT wheels forward"  0.5 -0.5 2
run "RIGHT wheels backward" -0.5 0.5 2
run "BOTH forward"          0.8  0   2
run "spin RIGHT in place"   0    0.8 2
echo "done"
