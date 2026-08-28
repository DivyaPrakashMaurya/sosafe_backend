# # walk+cab+ride--------

# import os
# import requests
# import uuid
# import logging
# from typing import Literal
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from dotenv import load_dotenv

# # Production logger configuration setup
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# load_dotenv()
# OLA_API_KEY = os.getenv("OLA_API_KEY")

# app = FastAPI(title="Safe Journey - Ola Maps Production Engine V3")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ─── APP-LEVEL MODE → OLA MAPS MODE MAPPING ───
# # `mode` in RouteRequest is the app's own vocabulary (walking / driving /
# # ride), matching what each Flutter view model already sends. This gets
# # translated to whatever value Ola Maps' Directions API actually expects
# # before the upstream call.
# #
# # IMPORTANT: Ola Maps' public docs don't clearly document a dedicated
# # two-wheeler/bike routing profile (unlike, say, Google's TWO_WHEELER travel
# # mode). Until that's confirmed against Ola's interactive API reference
# # (https://maps.olakrutrim.com/apidocs#tag/routing-apis), "ride" mode is
# # routed using the same "driving" profile as cab mode — this will give a
# # usable route/ETA, just not one optimized for two-wheeler-only shortcuts.
# # If Ola exposes a bike/two-wheeler-specific mode value later, update this
# # one mapping and every feature (walking/cab/ride) picks it up automatically.
# APP_MODE_TO_OLA_MODE: dict[str, str] = {
#     "walking": "walking",
#     "driving": "driving",  # used by cab mode
#     "ride": "driving",     # used by ride (two-wheeler) mode — see note above
# }


# class RouteRequest(BaseModel):
#     start_lat: float
#     start_lng: float
#     end_lat: float
#     end_lng: float
#     # Restricting this to a Literal (instead of a bare str) means FastAPI
#     # rejects an unrecognized mode with a clean 422 instead of silently
#     # forwarding a typo straight to Ola Maps and getting back a confusing
#     # 502 further down the line.
#     mode: Literal["walking", "driving", "ride"] = "walking"
#     added_buffer_mins: int = 0
#     checkpoint_count: int = 2


# @app.get("/")
# def home():
#     return {"status": "running", "engine": "Ola Maps Hardened Production Active"}



# # ─── 1. OLA MAPS AUTOCOMPLETE ───
# @app.get("/api/v1/location/search")
# async def search_location(query: str = Query(..., description="Text typed by user")):
#     if not OLA_API_KEY:
#         raise HTTPException(status_code=500, detail="Ola API Key is missing in backend setup.")

#     url = "https://api.olamaps.io/places/v1/autocomplete"
#     params = {"input": query, "api_key": OLA_API_KEY}
#     headers = {"X-Request-Id": str(uuid.uuid4())}

#     try:
#         response = requests.get(url, params=params, headers=headers, timeout=10)
#         response.raise_for_status()
#         data_json = response.json()
        
#         if "predictions" not in data_json:
#             logger.warning(f"Unexpected Autocomplete structure response structure: {data_json}")
#             return {"status": "success", "results": []}

#         suggestions = []
#         for item in data_json["predictions"]:
#             suggestions.append({
#                 "place_name": item.get("description"),
#                 "place_id": item.get("place_id")  
#             })
            
#         return {"status": "success", "results": suggestions}
#     except requests.exceptions.RequestException as req_err:
#         logger.error(f"Autocomplete Network/API Error: {str(req_err)}")
#         raise HTTPException(status_code=502, detail=f"Upstream Map Service Error: {str(req_err)}")


# # ─── 2. OLA MAPS CONVERT PLACE_ID TO LAT-LNG ───
# @app.get("/api/v1/location/coordinates")
# async def get_coordinates(place_id: str):
#     if not OLA_API_KEY:
#         raise HTTPException(status_code=500, detail="Ola API Key is missing.")

#     url = "https://api.olamaps.io/places/v1/details"
#     params = {"place_id": place_id, "api_key": OLA_API_KEY}
#     headers = {"X-Request-Id": str(uuid.uuid4())}
    
#     try:
#         response = requests.get(url, params=params, headers=headers, timeout=10)
#         response.raise_for_status()
#         data = response.json()
        
#         print("\n=== [DEBUG LOG] OLA PLACES DETAILS ACTUAL RESPONSE ===")
#         print(data)
#         print("======================================================\n")
        
#         result_node = data.get("result", {})
#         geometry_node = result_node.get("geometry", {})
#         location_node = geometry_node.get("location", {})
        
#         lat = location_node.get("lat")
#         lng = location_node.get("lng")
        
#         return {
#             "status": "success",
#             "latitude": lat if lat else 0.0,
#             "longitude": lng if lng else 0.0,
#             "raw_debug_captured": True
#         }
#     except requests.exceptions.RequestException as req_err:
#         logger.error(f"Coordinates Core Endpoint Error: {str(req_err)}")
#         raise HTTPException(status_code=502, detail="Failed to fetch node locations coordinates.")


# # ─── 3. OLA MAPS REVERSE GEOCODING (LAT-LNG TO ADDRESS) ───
# @app.get("/api/v1/location/reverse")
# async def reverse_geocode(lat: float, lng: float):
#     if not OLA_API_KEY:
#         raise HTTPException(status_code=500, detail="Ola API Key is missing.")

#     url = "https://api.olamaps.io/places/v1/reverse-geocode"
#     params = {
#         "latlng": f"{lat},{lng}",
#         "api_key": OLA_API_KEY
#     }
#     headers = {"X-Request-Id": str(uuid.uuid4())}

#     try:
#         response = requests.get(url, params=params, headers=headers, timeout=10)
#         response.raise_for_status()
#         data = response.json()
        
#         if "results" in data and data["results"]:
#             address = data["results"][0].get("formatted_address", "Unknown Location")
#             return {"status": "success", "address": address}
        
#         return {"status": "success", "address": "Current Location Fetched"}
#     except Exception as e:
#         logger.error(f"Reverse Geocoding Error: {str(e)}")
#         return {"status": "error", "address": "Current Location"}   

# @app.post("/api/v1/route/calculate")
# async def calculate_route(data: RouteRequest):
#     if not OLA_API_KEY:
#         raise HTTPException(status_code=500, detail="Ola API Key is missing.")

#     # Translate the app's mode vocabulary (walking / driving / ride) into
#     # whatever Ola Maps' Directions API actually expects. See
#     # APP_MODE_TO_OLA_MODE above for why "ride" currently maps to "driving".
#     ola_mode = APP_MODE_TO_OLA_MODE.get(data.mode, data.mode)

#     url = "https://api.olamaps.io/routing/v1/directions"
#     params = {
#         "origin": f"{data.start_lat},{data.start_lng}",
#         "destination": f"{data.end_lat},{data.end_lng}",
#         "mode": ola_mode,
#         "api_key": OLA_API_KEY
#     }
#     headers = {
#         "X-Request-Id": str(uuid.uuid4()),
#         "Content-Type": "application/json"
#     }

#     try:
#         response = requests.post(url, params=params, headers=headers, timeout=15)
#         response.raise_for_status()
#         route_data = response.json()
        
#         if "routes" not in route_data or not route_data["routes"]:
#             raise HTTPException(status_code=400, detail="Invalid coordinates response.")
            
#         primary_route = route_data["routes"][0]
#         legs = primary_route["legs"][0]
        
#         duration_seconds = legs.get("duration", 0)
#         distance_meters = legs.get("distance", 0)
        
#         ola_raw_mins = round(duration_seconds / 60)
        
#         # ─── CORE PREFERENCE MATHEMATICS ENGINE ───
#         total_duration_mins = ola_raw_mins + data.added_buffer_mins
        
#         divisor = data.checkpoint_count + 1
#         safety_interval_mins = round(total_duration_mins / divisor, 2)
        
#         trigger_intervals = []
#         for i in range(1, data.checkpoint_count + 1):
#             trigger_intervals.append(round(safety_interval_mins * i, 1))

#         # 🎯 TESTING LIVE TERMINAL PRINTS
#         print("\n" + "="*50)
#         print(f"=== [ROUTE LOG] App Mode: {data.mode} (Ola mode: {ola_mode}) | Total Time: {total_duration_mins}m ===")
#         print(f"Trigger Schedule Minutes: {trigger_intervals}")
#         print("="*50 + "\n")

#         return {
#             "status": "success",
#             "data": {
#                 "mode": data.mode,
#                 "ola_raw_mins": ola_raw_mins,
#                 "total_duration_mins": total_duration_mins,
#                 "distance_km": round(distance_meters / 1000, 2),
#                 "checkpoint_count": data.checkpoint_count,
#                 "safety_interval_mins": safety_interval_mins,
#                 "trigger_schedule": trigger_intervals,
#                 "overview_polyline": primary_route.get("overview_polyline", "") 
#             }
#         }
#     except requests.exceptions.RequestException as req_err:
#         logger.error(f"Directions API Engine Failure: {str(req_err)}")
#         raise HTTPException(status_code=502, detail="Routing upstream calculation interface timed out.")


import os
import requests
import uuid
import logging
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 🚀 1. NEW IMPORT FOR CASCADING SOS ROUTER
from routers import sos_router

# Production logger configuration setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
OLA_API_KEY = os.getenv("OLA_API_KEY")

app = FastAPI(title="Safe Journey - Ola Maps Production Engine V3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 2. REGISTER THE SOS CASCADING ROUTER
app.include_router(sos_router.router)


# ─── APP-LEVEL MODE → OLA MAPS MODE MAPPING ───
APP_MODE_TO_OLA_MODE: dict[str, str] = {
    "walking": "walking",
    "driving": "driving",  # used by cab mode
    "ride": "driving",     # used by ride (two-wheeler) mode
}


class RouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    mode: Literal["walking", "driving", "ride"] = "walking"
    added_buffer_mins: int = 0
    checkpoint_count: int = 2


@app.get("/")
def home():
    return {"status": "running", "engine": "Ola Maps Hardened Production Engine + SOS Cascading Active"}


# ─── 1. OLA MAPS AUTOCOMPLETE ───
@app.get("/api/v1/location/search")
async def search_location(query: str = Query(..., description="Text typed by user")):
    if not OLA_API_KEY:
        raise HTTPException(status_code=500, detail="Ola API Key is missing in backend setup.")

    url = "https://api.olamaps.io/places/v1/autocomplete"
    params = {"input": query, "api_key": OLA_API_KEY}
    headers = {"X-Request-Id": str(uuid.uuid4())}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data_json = response.json()
        
        if "predictions" not in data_json:
            logger.warning(f"Unexpected Autocomplete structure response structure: {data_json}")
            return {"status": "success", "results": []}

        suggestions = []
        for item in data_json["predictions"]:
            suggestions.append({
                "place_name": item.get("description"),
                "place_id": item.get("place_id")  
            })
            
        return {"status": "success", "results": suggestions}
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Autocomplete Network/API Error: {str(req_err)}")
        raise HTTPException(status_code=502, detail=f"Upstream Map Service Error: {str(req_err)}")


# ─── 2. OLA MAPS CONVERT PLACE_ID TO LAT-LNG ───
@app.get("/api/v1/location/coordinates")
async def get_coordinates(place_id: str):
    if not OLA_API_KEY:
        raise HTTPException(status_code=500, detail="Ola API Key is missing.")

    url = "https://api.olamaps.io/places/v1/details"
    params = {"place_id": place_id, "api_key": OLA_API_KEY}
    headers = {"X-Request-Id": str(uuid.uuid4())}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print("\n=== [DEBUG LOG] OLA PLACES DETAILS ACTUAL RESPONSE ===")
        print(data)
        print("======================================================\n")
        
        result_node = data.get("result", {})
        geometry_node = result_node.get("geometry", {})
        location_node = geometry_node.get("location", {})
        
        lat = location_node.get("lat")
        lng = location_node.get("lng")
        
        return {
            "status": "success",
            "latitude": lat if lat else 0.0,
            "longitude": lng if lng else 0.0,
            "raw_debug_captured": True
        }
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Coordinates Core Endpoint Error: {str(req_err)}")
        raise HTTPException(status_code=502, detail="Failed to fetch node locations coordinates.")


# ─── 3. OLA MAPS REVERSE GEOCODING (LAT-LNG TO ADDRESS) ───
@app.get("/api/v1/location/reverse")
async def reverse_geocode(lat: float, lng: float):
    if not OLA_API_KEY:
        raise HTTPException(status_code=500, detail="Ola API Key is missing.")

    url = "https://api.olamaps.io/places/v1/reverse-geocode"
    params = {
        "latlng": f"{lat},{lng}",
        "api_key": OLA_API_KEY
    }
    headers = {"X-Request-Id": str(uuid.uuid4())}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and data["results"]:
            address = data["results"][0].get("formatted_address", "Unknown Location")
            return {"status": "success", "address": address}
        
        return {"status": "success", "address": "Current Location Fetched"}
    except Exception as e:
        logger.error(f"Reverse Geocoding Error: {str(e)}")
        return {"status": "error", "address": "Current Location"}   


# ─── 4. OLA MAPS ROUTE CALCULATOR ───
@app.post("/api/v1/route/calculate")
async def calculate_route(data: RouteRequest):
    if not OLA_API_KEY:
        raise HTTPException(status_code=500, detail="Ola API Key is missing.")

    ola_mode = APP_MODE_TO_OLA_MODE.get(data.mode, data.mode)

    url = "https://api.olamaps.io/routing/v1/directions"
    params = {
        "origin": f"{data.start_lat},{data.start_lng}",
        "destination": f"{data.end_lat},{data.end_lng}",
        "mode": ola_mode,
        "api_key": OLA_API_KEY
    }
    headers = {
        "X-Request-Id": str(uuid.uuid4()),
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        route_data = response.json()
        
        if "routes" not in route_data or not route_data["routes"]:
            raise HTTPException(status_code=400, detail="Invalid coordinates response.")
            
        primary_route = route_data["routes"][0]
        legs = primary_route["legs"][0]
        
        duration_seconds = legs.get("duration", 0)
        distance_meters = legs.get("distance", 0)
        
        ola_raw_mins = round(duration_seconds / 60)
        
        total_duration_mins = ola_raw_mins + data.added_buffer_mins
        
        divisor = data.checkpoint_count + 1
        safety_interval_mins = round(total_duration_mins / divisor, 2)
        
        trigger_intervals = []
        for i in range(1, data.checkpoint_count + 1):
            trigger_intervals.append(round(safety_interval_mins * i, 1))

        print("\n" + "="*50)
        print(f"=== [ROUTE LOG] App Mode: {data.mode} (Ola mode: {ola_mode}) | Total Time: {total_duration_mins}m ===")
        print(f"Trigger Schedule Minutes: {trigger_intervals}")
        print("="*50 + "\n")

        return {
            "status": "success",
            "data": {
                "mode": data.mode,
                "ola_raw_mins": ola_raw_mins,
                "total_duration_mins": total_duration_mins,
                "distance_km": round(distance_meters / 1000, 2),
                "checkpoint_count": data.checkpoint_count,
                "safety_interval_mins": safety_interval_mins,
                "trigger_schedule": trigger_intervals,
                "overview_polyline": primary_route.get("overview_polyline", "") 
            }
        }
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Directions API Engine Failure: {str(req_err)}")
        raise HTTPException(status_code=502, detail="Routing upstream calculation interface timed out.")