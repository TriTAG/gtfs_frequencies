# Transit frequency map generator

Generate a map of service frequencies for route segments in a GTFS dataset.

## Dependencies

* pyproj
* shapely

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

https://gist.github.com/mboos/2886d6094893e99aec07
