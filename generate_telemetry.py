import csv
import math

def make_csv(path, lat_start, lon_start, name):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['timestamp', 'latitude', 'longitude', 'heading'])
        for i in range(20):
            w.writerow([1700000000 + i*10, lat_start + i*0.001, lon_start - i*0.001, 45.0])

make_csv('data/survey2/telemetry.csv', 28.3, -88.0, 'survey2')
make_csv('data/survey3/telemetry.csv', 37.8, -122.4, 'survey3')
