"""模拟器路由"""

from fastapi import APIRouter, HTTPException

from api.models.simulator import SimulationRequest, SimulationResponse
from api.services import simulator_service

router = APIRouter()


@router.post("/run", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    try:
        return simulator_service.run_simulation_service(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模拟失败: {e}")


@router.post("/walk-forward", response_model=dict)
def run_walk_forward(req: SimulationRequest):
    try:
        return simulator_service.run_walk_forward_service(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Walk-forward 寻优失败: {e}")
