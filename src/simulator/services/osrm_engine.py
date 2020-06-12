"""Modified RoutingService.route to accept od_pairs list and make asynchronous requests to it"""

import polyline
from .async_requester import AsyncRequester
from config.settings import OSRM_HOSTPORT
from common.mesh import convert_xy_to_lonlat

class OSRMEngine(object):
    """Sends and parses asynchronous requests from list of O-D pairs"""
    def __init__(self, n_threads=8):
        self.async_requester = AsyncRequester(n_threads)
        self.route_cache = {}

    def nearest_road(self, points):
        """Input list of Origin-Destination latlong pairs, return
        tuple of (trajectory latlongs, distance, triptime)"""
        urllist = [self.get_nearest_url(point) for point in points]
        responses = self.async_requester.send_async_requests(urllist)
        resultlist = []
        for res in responses:
            nearest_point = res["waypoints"][0]
            location = nearest_point["location"]
            distance = nearest_point["distance"]
            resultlist.append((location, distance))
            print(f"distance : {distance}")

        return resultlist

    def route(self, od_list, decode=True):
        """Input list of Origin-Destination latlong pairs, return
        tuple of (trajectory latlongs, distance, triptime)"""
        urllist = [self.get_route_url(origin, destin) for origin, destin in od_list]
        responses = self.async_requester.send_async_requests(urllist)
        resultlist = []
        for res in responses:
            route = res["routes"][0]
            triptime = route["duration"]
            if decode:
                trajectory = polyline.decode(route['geometry'])
            else:
                trajectory = route['geometry']
            resultlist.append((trajectory, triptime))

        return resultlist

    def get_route_cache(self, l, a):
        if l in self.route_cache:
            if a in self.route_cache[l]:
                trajectory, triptime = self.route_cache[l][a]
                return trajectory[:], triptime
        else:
            self.route_cache[l] = {}
        x, y = l
        ax, ay = a
        origin = convert_xy_to_lonlat(x, y)
        destin = convert_xy_to_lonlat(x + ax, y + ay)
        self.route_cache[l][a] = self.route([(origin, destin)])[0]
        trajectory, triptime = self.route_cache[l][a]
        return trajectory[:], triptime


    def eta_one_to_many(self, origin_destins_list):
        urllist = [self.get_eta_one_to_many_url([origin] + destins) for origin, destins in origin_destins_list]
        responses = self.async_requester.send_async_requests(urllist)
        resultlist = []
        for res in responses:
            eta_list = res["durations"][0][1:]
            resultlist.append(eta_list)
        return resultlist

    def eta_many_to_one(self, origins_destin_list):
        urllist = [self.get_eta_one_to_many_url(origins + [destin]) for origins, destin in origins_destin_list]
        responses = self.async_requester.send_async_requests(urllist)
        resultlist = []
        for res in responses:
            eta_list = [d[0] for d in res["durations"][:-1]]
            resultlist.append(eta_list)
        return resultlist

    def eta_many_to_many(self, origins, destins):
        url = self.get_eta_many_to_many_url(origins, destins)
        res = self.async_requester.send_async_requests([url])[0]
        try:
            eta_matrix = res["durations"]
        except:
            print(origins, destins, res)
            raise
        return eta_matrix


    def get_route_url(cls, from_latlon, to_latlon):
        """Get URL for osrm backend call for arbitrary to/from latlong pairs"""
        urlholder = """http://{hostport}/route/v1/driving/{lon0},{lat0};{lon1},{lat1}?overview=full""".format(
            hostport=OSRM_HOSTPORT,
            lon0=from_latlon[1],
            lat0=from_latlon[0],
            lon1=to_latlon[1],
            lat1=to_latlon[0]
            )
        return urlholder


    def get_nearest_url(cls, latlon):
        urlholder = """http://{hostport}/nearest/v1/driving/{lon},{lat}?number=1""".format(
            hostport=OSRM_HOSTPORT,
            lon=latlon[1],
            lat=latlon[0]
            )
        return urlholder

    def get_eta_one_to_many_url(cls, latlon_list):
        urlholder = """http://{hostport}/table/v1/driving/polyline({coords})?sources=0""".format(
            hostport=OSRM_HOSTPORT,
            coords=polyline.encode(latlon_list, 5)
        )
        return urlholder

    def get_eta_many_to_one_url(cls, latlon_list):
        urlholder = """http://{hostport}/table/v1/driving/polyline({coords})?destinations={last_idx}""".format(
            hostport=OSRM_HOSTPORT,
            coords=polyline.encode(latlon_list, 5),
            last_idx=len(latlon_list) - 1
        )
        return urlholder

    def get_eta_many_to_many_url(cls, from_latlon_list, to_latlon_list):
        latlon_list = from_latlon_list + to_latlon_list
        ids = range(len(latlon_list))
        urlholder = """http://{hostport}/table/v1/driving/polyline({coords})?sources={sources}&destinations={destins}""".format(
            hostport=OSRM_HOSTPORT,
            coords=polyline.encode(latlon_list, 5),
            sources=';'.join(map(str, ids[:len(from_latlon_list)])),
            destins=';'.join(map(str, ids[len(from_latlon_list):]))
        )
        return urlholder
