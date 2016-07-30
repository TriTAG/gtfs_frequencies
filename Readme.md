# Transit frequency map generator

Generate a map of service frequencies for route segments in a GTFS dataset.

## Dependencies

* pyproj
* shapely
* colour

## Running

```
usage: process_frequencies.py [-h] [--utm UTM] folder calendar [calendar ...]

GTFS frequency map generator

positional arguments:
  folder      GTFS folder
  calendar    calendars to use in determining route frequency

optional arguments:
  -h, --help  show this help message and exit
  --utm UTM   UTM projection zone
```
## Example output

![Grand River Transit frequency map](https://raw.githubusercontent.com/TriTAG/gtfs_frequencies/master/map_example.png)

https://gist.github.com/mboos/2886d6094893e99aec07
