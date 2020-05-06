import pandas as pd
import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
from common.time_utils import get_local_datetime, get_local_unixtime
from common.geoutils import great_circle_distance
from config.settings import BOUNDING_BOX

def load_trip_data(path, cols, new_cols):
    df = pd.read_csv(path, usecols=cols, nrows=None)
    df.rename(columns=dict(zip(cols, new_cols)), inplace=True)
    return df

def convert_datetime(df):
    df['request_datetime'] = pd.to_datetime(df.pickup_datetime).apply(lambda x: int(get_local_unixtime(x)))
    df['trip_time'] = pd.to_datetime(df.dropoff_datetime).apply(lambda x: int(get_local_unixtime(x))) - df.request_datetime
    df = df.drop(['pickup_datetime', 'dropoff_datetime'], axis=1)
    return df


def remove_outliers(df):
    df['distance'] = great_circle_distance(df.origin_lat, df.origin_lon, df.destination_lat, df.destination_lon).astype(int)
    df['speed'] = df.distance / df.trip_time / 1000 * 3600 # km/h

    l0 = len(df)
    print('original len : ' + str(l0))
    df = df[(df.trip_time > 60) & (df.trip_time < 3600 * 2)]
    l1 = len(df)
    print('after trip_time : ' + str(l0-l1))
    df = df[(df.distance > 100) & (df.distance < 100000)]

    l2 = len(df)
    print('after distance : ' + str(l1 - l2))

    df = df[(df.speed > 2) & (df.speed < 80)]

    l3 = len(df)
    print('after speed : ' + str(l2 - l2))

    df = df[(df.fare < 200) & (df.fare > 10)]

    l4 = len(df)
    print('after rpm : ' + str(l3 - l4))

    return df.drop(['distance', 'speed'], axis=1)

def extract_bounding_box(df, bounding_box):
    min_lat, min_lon = bounding_box[0]
    max_lat, max_lon = bounding_box[1]
    df = df[(df.origin_lat > min_lat) &
            (df.origin_lat < max_lat) &
            (df.origin_lon > min_lon) &
            (df.origin_lon < max_lon)]
    df = df[(df.destination_lat > min_lat) &
            (df.destination_lat < max_lat) &
            (df.destination_lon > min_lon) &
            (df.destination_lon < max_lon)]
    return df

def create_dataset(logs_path, bounding_box):
    logs_cols = ['picked_at', 'delivered_at', 'res_longitude', 'res_latitude', 'user_saved_longitude', 'user_saved_latitude','fare']
    new_cols = ['pickup_datetime', 'dropoff_datetime', 'origin_lon', 'origin_lat', 'destination_lon', 'destination_lat']
    saved_cols = ['request_datetime', 'trip_time', 'origin_lon', 'origin_lat', 'destination_lon', 'destination_lat', 'fare']

    # Load green and yellow taxi trip data and merge them
    df = load_trip_data(logs_path, logs_cols, new_cols)
    print("Load: {} records".format(len(df)))

    df = extract_bounding_box(df, bounding_box)
    df = convert_datetime(df)
    df = remove_outliers(df)
    df.sort_values(by='request_datetime', ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df = df[saved_cols]
    df.index.name = "id"
    print("After Cleaning: {} records".format(len(df)))
    return df

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("data", help = "data directory")
    parser.add_argument("--month", help = "year-month")
    args = parser.parse_args()

    DATA_PATH = '{}/logs_data_{}.csv'.format(args.data, args.month)
    OUTPUT_PATH = '{}/trips_{}.csv'.format(args.data, args.month)
    df = create_dataset(DATA_PATH, BOUNDING_BOX)
    print("Saving DataFrame containing {} rows".format(len(df)))
    df.to_csv(OUTPUT_PATH)
