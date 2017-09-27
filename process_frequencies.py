"""GTFS frequency map generator."""

import os
from shapely.geometry import LineString, mapping
from shapely.ops import linemerge, transform
from functools import partial
import json
import pyproj
import argparse

import random
from colour import Color


def get_random_color(pastel_factor=0.5):
    """Generate a random color."""
    return [(x+pastel_factor) / (1.0+pastel_factor)
            for x in [random.uniform(0, 1) for i in [1, 2, 3]]]


def color_distance(c1, c2):
    """Determine distance from another colour."""
    return sum([abs(x[0]-x[1]) for x in zip(c1, c2)])


def generate_new_color(existing_colors, pastel_factor=0.5):
    """Generate a random colour distinct from other colours in use."""
    max_distance = None
    best_color = None
    for i in range(0, 100):
        color = get_random_color(pastel_factor=pastel_factor)
        if not existing_colors:
            return color
        best_distance = min([color_distance(color, c)
                            for c in existing_colors])
        if not max_distance or best_distance > max_distance:
            max_distance = best_distance
            best_color = color
    return best_color


def diff_layers(geom1, geom2):
    """Find the difference between two transit trips."""
    g1diff = geom1['line'].difference(geom2['line'])
    if g1diff.type == 'LineString' and g1diff > TOL:
        return [dict(line=g1diff, count=geom1['count'])]
    elif g1diff.type == 'MultiLineString':
        merge = linemerge(g1diff)
        if merge.type == 'LineString':
            merge = [merge]
        return [dict(line=g, count=geom1['count'])
                for g in merge if g.length > TOL]
    else:
        return []


def merge_layers(geom1, geom2):
    """Find the overlapping portions of two transit trips."""
    g2l = geom2['line'].buffer(bTol)  # snap(geom2['line'], geom1['line'], TOL)
    intersect_geom = geom1['line'].intersection(g2l)
    if intersect_geom.type == 'LineString':
        if intersect_geom.length > TOL:
            intersect = [intersect_geom]
        else:
            intersect = []
    elif intersect_geom.type == 'Point':
        intersect = []
    else:
        intersect = [g for g in intersect_geom
                     if g.type != 'Point' and g.length > TOL]
        if intersect:
            intersect = linemerge(intersect)
            if intersect.type == 'LineString':
                intersect = [intersect]
            else:
                intersect = list(intersect)
            intersect = [g for g in intersect if g.length > TOL]
    if not intersect:
        return [], [geom1, geom2]
    else:
        count = geom1['count'] + geom2['count']
        intersect = [dict(line=g, count=count) for g in intersect]
        sg1 = {'count': geom2['count'], 'line': geom1['line'].buffer(bTol)}
        sg2 = {'count': geom2['count'], 'line': g2l}
        g1 = diff_layers(geom1, sg2)
        g2 = diff_layers(geom2, sg1)
        return [intersect, g1 + g2]


def load_shapes(GTFS_DIR, proj):
    """Load GTFS file shapes.txt."""
    shapes = {}
    index = {}
    with open(os.path.join(GTFS_DIR, 'shapes.txt')) as fp:
        for line in fp:
            tokens = map(str.strip, line.split(','))
            if 'shape_id' in tokens:
                for i, heading in enumerate(tokens):
                    index[heading] = i
            else:
                shape_id = tokens[index['shape_id']]
                lat = float(tokens[index['shape_pt_lat']])
                lon = float(tokens[index['shape_pt_lon']])
                lon, lat = proj(lon, lat)
                seq = int(tokens[index['shape_pt_sequence']])
                if shape_id not in shapes:
                    shapes[shape_id] = {'coords': {}, 'count': 0}
                shapes[shape_id]['coords'][seq] = {'lon': lon, 'lat': lat}

    for shape in shapes.itervalues():
        points = []
        for seq in sorted(shape['coords']):
            points.append((shape['coords'][seq]['lon'],
                           shape['coords'][seq]['lat']))
        shape['line'] = LineString(points)  # .simplify(tolerance=2)
    return shapes


def load_trips(shapes, calendars, GTFS_DIR, proj):
    """Load GTFS file trips.txt."""
    index = {}
    with open(os.path.join(GTFS_DIR, 'trips.txt')) as fp:
        for line in fp:
            tokens = map(str.strip, line.split(','))
            if 'trip_id' in tokens:
                for i, heading in enumerate(tokens):
                    index[heading] = i
            elif tokens[index['service_id']] in calendars:
                shape_id = tokens[index['shape_id']]
                if shape_id:
                    shapes[shape_id]['count'] += 1
                    shapes[shape_id]['route'] = int(tokens[index['route_id']])

TOL = 5
bTol = 1


def main():
    """Load GTFS data and figure out frequencies of route segments."""
    parser = argparse.ArgumentParser(
        description='GTFS frequency map generator')
    parser.add_argument('folder',
                        help='GTFS folder')
    parser.add_argument('calendars', nargs='+', metavar='calendar',
                        help='calendars to use in determining route frequency')
    parser.add_argument('--utm', type=int, default=17,
                        help='UTM projection zone')

    args = parser.parse_args()

    # GTFS_DIR = 'GRT_GTFS'
    # CALENDARS = ['16WINT-All-Weekday-02', '16WINT-All-Weekday-02-1111000']
    GTFS_DIR = args.folder
    CALENDARS = args.calendars

    proj = pyproj.Proj(proj='utm', zone=args.utm, ellps='WGS84')
    project = partial(
        pyproj.transform,
        proj,
        pyproj.Proj(init='epsg:4326'))

    # Load trip data
    shapes = load_shapes(GTFS_DIR, proj)
    load_trips(shapes, CALENDARS, GTFS_DIR, proj)

    # Sort by route
    routes = {}
    for shape in shapes.itervalues():
        if 'route' in shape:
            if shape['route'] not in routes:
                routes[shape['route']] = []
            # split routes in two to avoid issues with 'loop on stick' routes'
            num_coords = len(shape['line'].coords)
            shape1 = {
                'count': shape['count'],
                'line': LineString(shape['line'].coords[:num_coords/2+1])
            }
            shape2 = {
                'count': shape['count'],
                'line': LineString(shape['line'].coords[num_coords/2:])
            }
            routes[shape['route']].append(shape1)
            routes[shape['route']].append(shape2)

    colours = [(1, 1, 0), (.5, .5, 0), (0.878, 0.984, 0.957)]
    all_routes = {"type": "FeatureCollection", "features": []}
    # For each route, merge trips that overlap
    for route_id, shape_list in routes.iteritems():
        print "Route {0}".format(route_id)
        # need an algorithm here that will compare every item with every other
        # item and merge/split, and then repeat with merge/splits
        seed_list = shape_list
        unique_list = []

        while seed_list:
            merged_list = []
            candidate = seed_list[0]
            foundMatch = False
            for shape in seed_list[1:]:
                if foundMatch:
                    merged_list.append(shape)
                else:
                    intersect, uniques = merge_layers(candidate, shape)
                    if intersect:
                        merged_list += intersect
                        merged_list += uniques
                        foundMatch = True
                    else:
                        merged_list.append(shape)
            if not foundMatch:
                unique_list.append(candidate)
            seed_list = merged_list

        segments = {}
        for shape in unique_list:
            cnt = shape['count']
            if cnt not in segments:
                segments[cnt] = []
            segments[cnt].append(shape)
        unique_list = []
        for cnt in segments:
            unique_list.append({
                'count': cnt,
                'line': linemerge([s['line'] for s in segments[cnt]])
            })
        routes[route_id] = unique_list

        new_colour = Color(rgb=generate_new_color(colours, pastel_factor=0.1))
        colours.append(new_colour.rgb)

        fc = {"type": "FeatureCollection", "features": []}
        for shape in unique_list:
            line = shape['line'].simplify(3, preserve_topology=True)
            feat = {
                'type': 'Feature',
                'geometry': mapping(transform(project, shape['line']))
            }
            feat['properties'] = {'count': shape['count'],
                                  'stroke-width': 10.0 * shape['count'] / 200.,
                                  'route': route_id,
                                  'stroke': new_colour.hex}

            fc['features'].append(feat)
            if route_id < 300:
                all_routes['features'].append(feat)
        with open(os.path.join('dump_data',
                  '{0}.geojson'.format(route_id)), 'w') as fp:
            json.dump(fc, fp)

    with open(os.path.join('dump_data', 'grt.geojson'), 'w') as fp:
            json.dump(all_routes, fp)

if __name__ == '__main__':
    main()
