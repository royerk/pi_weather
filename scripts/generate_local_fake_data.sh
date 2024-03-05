#!/bin/bash

# Get the current date and time
current_time=$(date +"%Y-%m-%d %H:%M:%S")

# Loop over the last 24 hours
for ((i=0; i<24; i++)); do
    # Calculate the date and time for the current iteration
    date_time=$(date -d "$current_time -$i hours" +"%Y-%m-%d %H:%M:%S")
    
    # Execute the curl command with the calculated date and time
    curl -X POST -H "Content-Type: application/json" -d '{
        "device_name": "toto",
        "temperature": 20.0,
        "humidity": 50.0,
        "pressure": 1013.25,
        "date": "'"$date_time"'"
    }' http://172.17.0.2:5000/v1/data_point/add
done

for ((i=0; i<24; i++)); do
    # Calculate the date and time for the current iteration
    date_time=$(date -d "$current_time -$i hours" +"%Y-%m-%d %H:%M:%S")
    
    # Execute the curl command with the calculated date and time
    curl -X POST -H "Content-Type: application/json" -d '{
        "device_name": "titi",
        "temperature": 25.0,
        "humidity": 50.0,
        "pressure": 1010.25,
        "date": "'"$date_time"'"
    }' http://172.17.0.2:5000/v1/data_point/add
done
