"""
Created on Thu Feb  5  2023
@author: Armagan /ml_lab
"""

import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import requests
import folium

import sys
import os

from pathlib import Path 

import matplotlib.cm as cm
import random



############################################################################################################

def get_directions_response(lat1, long1, lat2, long2, mode='bus'):
   url = "https://route-and-directions.p.rapidapi.com/v1/routing"
   key = "13aadd043bmsh7e8ca17913040f0p1d9420jsn496bf07a9d7b"
   host = "route-and-directions.p.rapidapi.com"
   headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}
   querystring = {"waypoints":f"{str(lat1)},{str(long1)}|{str(lat2)},{str(long2)}","mode":mode}
   response = requests.request("GET", url, headers=headers, params=querystring)
   return response

# response_test = get_directions_response(52.4013, 4.5425, 52.402, 4.5426) 

############################################################################################################
# INPUT VARIABLES

# path to the Algorithm output excel file
bus_stop_excel_path = r'Visualization/Inputs/Bus_stops.xlsx'

############################################################################################################

"""
Preprocessing

Getting all the combined bus stops from 2 excel files
"""
def preprocess_xlsx():

   from Preprocessing.preprocess_xlsx import preprocess_xlsx

   _, _, _, _, _, students_df_agg, _, _, _, _, _, _, _, _, _, _, _, _, _ = preprocess_xlsx()
   origin_stops = students_df_agg[['origin_stop', 'origin_stop_id', 'origin_stop_latitude', 'origin_stop_longitude']].copy()
   origin_stops = origin_stops.rename(columns={"origin_stop": "stop_name", "origin_stop_id": "stop_id", "origin_stop_latitude": "stop_latitude", "origin_stop_longitude": "stop_longitude"})
   school_stops = students_df_agg[['school_stop', 'school_stop_id', 'school_stop_latitude', 'school_stop_longitude']].copy()
   school_stops = school_stops.rename(columns={"school_stop": "stop_name", "school_stop_id": "stop_id", "school_stop_latitude": "stop_latitude", "school_stop_longitude": "stop_longitude"})
   stops_lon_lat = pd.concat([origin_stops, school_stops], axis=0)
   stops_lon_lat = stops_lon_lat.drop_duplicates()

   # create or update an excel file from stops_lon_lat df to Visualization folder
   stops_lon_lat.to_excel(bus_stop_excel_path, index=False)

   return stops_lon_lat

   print("done preprocessing")


############################################################################################################

def read_excels(algo_output_path):
   #### read the Algorithm output excel file
   algorithm_output_excel = pd.ExcelFile(algo_output_path)

   dict_bus_timetable = {}
   # for every sheet in the excel file, create a dataframe and add it to the dictionary
   for sheet in algorithm_output_excel.sheet_names:
      dict_bus_timetable[sheet] = pd.read_excel(algorithm_output_excel, sheet_name=sheet)

   # create a list of dataframes
   list_of_dfs = []
   for key in dict_bus_timetable:
      list_of_dfs.append(dict_bus_timetable[key])


   #### read the bus stops excel file
   bus_stops= pd.read_excel(bus_stop_excel_path)

   return dict_bus_timetable, bus_stops

#############################################################################################################

"""
For each of the bus in the dict_bus_timetable , except the first index
if bus_stops['stop_id'] equal to the "Station" column in the dataframe in the dictionary, 
then add the latitude and longitude of the bus stop as a new column in the dataframe

"""
def get_name_latitude_longitude(dict_bus_timetable, bus_stop_df):
   # delete the first key:value pair of the dict_bus_timetable
   del dict_bus_timetable[list(dict_bus_timetable.keys())[0]]

   # add the latitude and longitude columns to the dataframes in the dictionary
   for key in dict_bus_timetable:
      dict_bus_timetable[key]['stop_latitude'] = np.nan
      dict_bus_timetable[key]['stop_longitude'] = np.nan
      dict_bus_timetable[key]['stop_name'] = np.nan

   for key in dict_bus_timetable:
      for i in range(0, len(dict_bus_timetable[key])):
         for j in range(len(bus_stop_df)):
            if dict_bus_timetable[key]['Station'][i] == bus_stop_df['stop_id'][j]:
               dict_bus_timetable[key]['stop_name'][i] = bus_stop_df['stop_name'][j]
               dict_bus_timetable[key]['stop_latitude'][i] = bus_stop_df['stop_latitude'][j]
               dict_bus_timetable[key]['stop_longitude'][i] = bus_stop_df['stop_longitude'][j]
              
               
   return dict_bus_timetable


#############################################################################################################

"""
get_directions_response(lat1, long1, lat2, long2, mode='bus')

get direction response for each stations in the dataframe in the dictionary
the response is a direction between 2 latitudes and longitudes
"""

def get_directions_response_for_each_station(dict_bus_timetable, bus_limit = 0):
   # add the response column to the dataframes in the dictionary
   for key in dict_bus_timetable:
      dict_bus_timetable[key]['response'] = np.nan

   # limit the number of buses to be visualized
   if bus_limit != 0:
      dict_bus_timetable = dict(list(dict_bus_timetable.items())[:bus_limit])

   # get directions response for each station in the dataframe in the dictionary
   for key in dict_bus_timetable:
      for i in range(0, len(dict_bus_timetable[key])):
         if i < len(dict_bus_timetable[key])-1:
            response = get_directions_response(dict_bus_timetable[key]['stop_latitude'][i], dict_bus_timetable[key]['stop_longitude'][i], \
               dict_bus_timetable[key]['stop_latitude'][i+1], dict_bus_timetable[key]['stop_longitude'][i+1])
            dict_bus_timetable[key]['response'][i] = response
   return dict_bus_timetable

#############################################################################################################

"""
using folium map to visualize the bus routes

create map of the bus routes on the map based on the response in the dataframe in the dictionary
create marker at final bus stop with popup of the bus route number

"""
def generate_random_color():
   # didnt set until 0xFFFFFF (white) because its hard to see in the map
   return '#%06X' % random.randint(0, 0xFF00FF) 

def pick_random_marker_color():
   colors = {"gray", 'darkblue', 'purple', 'orange', 'red', 'darkgreen', 'blue', 'black', 'pink', 'lightred', 'darkred', 'cadetblue'}
   return random.choice(list(colors))

def pick_color_based_on_number(number):
   colors = {"gray", 'darkblue', 'purple', 'orange', 'red', 'darkgreen', 'blue', 'black', 'pink', 'lightred', 'darkred', 'cadetblue'}
   
   # if number is greater than the number of colors, then starts from the beginning
   if number >= len(colors):
      number = number % len(colors)
   else:
      number = number
   
   color = list(colors)[number]
   return color

def create_map(dict_bus_timetable, bus_limit = 0, start_pin = True, stop_pin=True):
   # limit the number of buses to be visualized
   m = folium.Map()
   color_counter = 0

   # limit the number of buses to be visualized
   if bus_limit != 0:
      dict_bus_timetable = dict(list(dict_bus_timetable.items())[:bus_limit])

   # enhance the dataframe, create a tuple called location based on the longitude and latitude
   for key in dict_bus_timetable:
      dict_bus_timetable[key]['location'] = list(zip(dict_bus_timetable[key]['stop_latitude'], dict_bus_timetable[key]['stop_longitude']))

   # create a map of the bus routes on the map based on the response in the dataframe in the dictionary
   # iterate through the dictionary and create a different color for each bus route
   # key = bus linie
   for key in dict_bus_timetable:
      marker_color = pick_color_based_on_number(color_counter)
      color_counter += 1

      # decrease opacity if the bus_limit is high
      if bus_limit > 0 and bus_limit <= 10:
         opacity = 0.6
         start_pin = True
         stop_pin = True
      elif bus_limit > 10 and bus_limit <= 50:
         opacity = 0.5
      elif bus_limit > 50 and bus_limit <= 100:
         opacity = 0.3
      elif bus_limit == 0:
         opacity = 0.2
      else:
         opacity = 1
      

      # create marker at final bus stop with popup of the bus route number
      if start_pin:
         folium.Marker(
         location=dict_bus_timetable[key]['location'][0], 
         popup=dict_bus_timetable[key]['stop_name'][0],
         icon = folium.Icon(color=marker_color, prefix = 'fa', icon='bus')).add_to(m)

      if stop_pin:
         folium.Marker(
            location=dict_bus_timetable[key]['location'][len(dict_bus_timetable[key])-1],\
            popup=dict_bus_timetable[key]['stop_name'][len(dict_bus_timetable[key])-1],\
            icon=folium.Icon(color=marker_color, prefix = 'fa', icon='school')).add_to(m)
         

      # iterate through the dataframe in the dictionary
      for i in range(0, len(dict_bus_timetable[key])):
         if i < len(dict_bus_timetable[key])-1:
            # get the response from the dataframe in the dictionary
            response = dict_bus_timetable[key]['response'][i]

            mls = response.json()['features'][0]['geometry']['coordinates']
            points = [(p[1], p[0]) for p in mls[0]]

            # create a polyline on the map
            folium.PolyLine(points, color=marker_color, weight=5, opacity=opacity, popup=key).add_to(m)

            # create optimal zoom
            zoom_df = pd.DataFrame(mls[0]).rename(columns={0:'Lon', 1:'Lat'})[['Lat', 'Lon']]
            sw = zoom_df[['Lat', 'Lon']].min().values.tolist()
            ne = zoom_df[['Lat', 'Lon']].max().values.tolist()
            m.fit_bounds([sw, ne])
               
   return m



