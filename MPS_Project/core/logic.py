from math import cos
from math import sin
import math
EARTH_RAD=6378

def convert_from_coord_str_to_degrees(coord):
    #Чтоб долго не думать как записи типа 12°34'56" N переводить в float вид
    minus=False
    coord=coord.lower()
    res=0
    if coord.count("w") or coord.count("s"):
        minus=True
    coord=coord.replace("w","").replace("e","").replace("n","").replace("s","")
    coord=coord.replace("''","″").replace("'","′").replace(" ","").replace("°",";").replace("′",";").replace("″",";").split(";")
    for i in range(min(3,len(coord))):
        res+=float(coord[i])/(60**i)
    if minus:
        return -1*res
    return  res

def haversine(lat1,long1,lat2,long2):
    #Это чтоб считать расстояние между 2 точками на шаре
    
    lat1 = math.radians(lat1)
    long1 = math.radians(long1)
    lat2 = math.radians(lat2)
    long2 = math.radians(long2)

    dlat = lat2-lat1
    dlong = long2-long1
    a = sin(dlat/2)**2+cos(lat1)*cos(lat2)*sin(dlong/2)**2
    c = 2*math.asin(math.sqrt(a))
    return c*EARTH_RAD

