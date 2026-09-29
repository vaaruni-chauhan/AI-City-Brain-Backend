from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket
)
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from database import (
    init_database,
    get_all_roads,
    get_road,
    update_road,
    add_incident,
    get_all_incidents,
    update_incident_status,
    save_traffic_history
)

from simulation import (
    create_initial_traffic,
    simulate_accident
)

from models import (
    TrafficUpdate,
    AccidentRequest,
    IncidentStatusUpdate
)

import asyncio
from datetime import datetime


# =================================
# CREATE FASTAPI APPLICATION
# =================================

app = FastAPI(
    title="AI City Brain Backend",
    description="Backend and traffic simulation system",
    version="1.0"
)


# =================================
# CONNECT FRONTEND
# =================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# =================================
# STARTUP
# =================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # STARTUP
    print("Starting AI City Brain...")
    init_database()
    print("Database initialized successfully.")

    # Create database tables
    init_database()

    # Create Road A, B and C
    create_initial_traffic()
     # SHUTDOWN
    print("AI City Brain shutting down...")


# =================================
# HOME
# =================================

@app.get("/")
def home():

    return {
        "message":
        "AI City Brain Backend is running"
    }


# =================================
# GET ALL TRAFFIC
# =================================

@app.get("/traffic")
def get_traffic():

    roads = get_all_roads()

    return {
        "roads": roads
    }


# =================================
# GET ONE ROAD
# =================================

@app.get("/traffic/{road_name}")
def get_single_road(
    road_name: str
):

    road = get_road(road_name)

    if road is None:

        raise HTTPException(
            status_code=404,
            detail="Road not found"
        )

    return road


# =================================
# UPDATE TRAFFIC
# =================================

@app.put("/traffic/{road_name}")
def update_traffic(
    road_name: str,
    data: TrafficUpdate
):

    road = get_road(road_name)

    if road is None:

        raise HTTPException(
            status_code=404,
            detail="Road not found"
        )

    updated = update_road(
        road_name,
        data.vehicle_count,
        data.average_speed,
        data.congestion
    )

    save_traffic_history(updated)

    return {
        "message":
        "Traffic updated successfully",

        "road":
        updated
    }


# =================================
# SIMULATE ACCIDENT
# =================================

@app.post("/accident")
def create_accident(
    request: AccidentRequest
):

    result = simulate_accident(
        request.road,
        request.severity
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Road not found"
        )

    # Store accident
    add_incident(
        road=request.road,

        incident_type="ACCIDENT",

        severity=request.severity,

        status="active"
    )

    # Save changed traffic
    for road in get_all_roads():

        save_traffic_history(road)

    return result


# =================================
# GET INCIDENTS
# =================================

@app.get("/incidents")
def get_incidents():

    return {
        "incidents":
        get_all_incidents()
    }


# =================================
# UPDATE INCIDENT
# =================================

@app.put("/incidents/{incident_id}")
def update_incident(
    incident_id: int,
    data: IncidentStatusUpdate
):

    update_incident_status(
        incident_id,
        data.status
    )

    return {
        "message":
        "Incident status updated"
    }


# =================================
# DASHBOARD DATA
# =================================

@app.get("/dashboard")
def dashboard():

    roads = get_all_roads()

    incidents = get_all_incidents()

    high_congestion = 0

    for road in roads:

        if road["congestion"] == "HIGH":

            high_congestion += 1

    active_incidents = 0

    for incident in incidents:

        if incident["status"] == "active":

            active_incidents += 1

    return {

        "total_roads":
        len(roads),

        "high_congestion_roads":
        high_congestion,

        "active_incidents":
        active_incidents,

        "roads":
        roads
    }


# =================================
# DATA SENT TO AI MEMBER
# =================================

@app.get("/ai/input")
def get_ai_input():

    roads = get_all_roads()

    incidents = get_all_incidents()

    active_incidents = [

        incident

        for incident in incidents

        if incident["status"] == "active"
    ]

    return {

        "timestamp":
        datetime.now().isoformat(),

        "traffic":
        roads,

        "active_incidents":
        active_incidents
    }


# =================================
# WEBSOCKET
# =================================

@app.websocket("/ws/traffic")
async def traffic_websocket(
    websocket: WebSocket
):

    await websocket.accept()

    try:

        while True:

            roads = get_all_roads()

            await websocket.send_json({

                "type":
                "traffic_update",

                "roads":
                roads
            })

            await asyncio.sleep(3)

    except Exception:

        await websocket.close()