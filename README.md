# Distributed Fleet Control Simulator
## Reference
* [MOVI: A Model-Free Approach to Dynamic Fleet Management](https://arxiv.org/pdf/1804.04758.pdf)
* [Distributed Fleet Control with Maximum Entropy
Deep Reinforcement Learning](https://openreview.net/pdf?id=SkxWcjx09Q)

## Setup
Below you will find step-by-step instructions to set up the NYC taxi simulation using 2016-05 trips for training and 2016-06 trips for evaluation.
**Please make more than 10 GB memory resource available to Docker Engine.** 
### 1. Download OSM Data
```commandline
wget https://download.bbbike.org/osm/bbbike/NewDelhi/NewDelhi.osm.pbf -P osrm
```

### 2. Preprocess OSM Data
```commandline
cd osrm
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/NewDelhi.osm.pbf
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/NewDelhi.osrm
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/NewDelhi.osrm
```

### 3. Download Trip Data
```commandline
mkdir data
cd data 
mkdir trip_records
```
Move your data inside data/trip_records
### 4. Build Docker image
```commandline
docker-compose build sim
```

### 5. Preprocess Trip Records
```commandline
docker-compose run --no-deps sim python src/preprocessing/preprocess_nyc_dataset.py ./data/trip_records/ --month <train_time>
docker-compose run --no-deps sim python src/preprocessing/preprocess_nyc_dataset.py ./data/trip_records/ --month <test_time>
```

### 6. Snap origins and destinations of all trips to OSM
```commandline
docker-compose run sim python src/preprocessing/snap_to_road.py ./data/trip_records/trips_<train_time>.csv ./data/trip_records/mm_trips_<train_time>.csv
docker-compose run sim python src/preprocessing/snap_to_road.py ./data/trip_records/trips_<test_time>.csv ./data/trip_records/mm_trips_<test_time>.csv
```

### 7. Create trip database for Simulation
```commandline
docker-compose run --no-deps sim python src/preprocessing/create_db.py ./data/trip_records/mm_trips_<test_time>.csv
```

### 8. Prepare statistical demand profile using training dataset
```commandline
docker-compose run --no-deps sim python src/preprocessing/create_profile.py ./data/trip_records/mm_trips_<train_time>.csv
```

### 9. Precompute trip time and trajectories by OSRM
```commandline
docker-compose run sim python src/preprocessing/create_tt_map.py ./data
```
The tt_map needs to be recreated when you change simulation settings such as MAX_MOVE.

### 10. Change simulation settings
You can find simulation setting files in `src/config/settings` and `src/dqn/settings`.

## Quick Start
### 1. Run Simulation using OSRM
This mode
```commandline
docker-compose up
```
`sim` container is created and runs `bin/run.sh`. 

### 2. Run Simulation using precomputed OSRM routing data
This mode uses precomputed ETA and trajectories by OSRM, which is much faster than above.
```commandline
docker-compose run --no-deps sim python src/run.py --train --tag test
```
