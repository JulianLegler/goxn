#!/bin/bash

# Check if the user provided an argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <number_of_iterations>"
  exit 1
fi

iterations=$1

for (( i=1; i<=iterations; i++ ))
do
  echo "Starting iteration $i..."
  
  # Record the start time in seconds since the epoch
  start_time=$(date +%s)
  
  # Run the experiment suite script and wait until it finishes
  ./run_experiment_suite.sh
  
  # Record the end time
  end_time=$(date +%s)
  
  # Calculate the duration
  duration=$((end_time - start_time))
  echo "Iteration $i finished in ${duration} seconds."
done
