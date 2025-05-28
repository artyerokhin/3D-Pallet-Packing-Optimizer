from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
from datetime import datetime

from src.utils.constants import STANDARD_BOXES, PackingMethod
from src.packers.weight_aware import WeightAwarePacker
from src.packers.extreme_points import ExtremePointPacker
from src.packers.laff import LAFFPacker
from src.packers.corner_points import CornerPointPacker
from src.packers.sfc import SFCPacker
from src.validation.validators import DataValidator
from py3dbp import Bin, Item

app = FastAPI(
    title="3D Bin Packing API",
    description="API для оптимизации упаковки коробок на поддон",
    version="1.0.0"
)  # Добавьте закрывающую скобку

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)  # Добавьте закрывающую скобку

tasks_storage = {}

# Встроенный класс для API (без Streamlit зависимостей)
class APIErrorHandler:
    @staticmethod
    def format_validation_errors(result) -> List[Dict[str, Any]]:
        """Форматирование ошибок валидации для API"""
        return [
            {
                "type": error.error_type.value,
                "message": error.message,
                "field": error.field,
                "value": error.value,
                "suggestion": error.suggestion
            }
            for error in result.errors
        ]

class BoxData(BaseModel):
    name: str
    length: float
    width: float
    height: float
    weight: float
    quantity: int = 1
    fragile: bool = False
    stackable: bool = True

class PalletData(BaseModel):
    length: float
    width: float
    height: float
    max_weight: float

class PackingRequest(BaseModel):
    pallet: PalletData
    boxes: List[BoxData]
    method: str = "Weight-Aware (стабильная укладка с учетом веса)"
    support_threshold: float = 0.8
    weight_check_enabled: bool = True

class PackingResult(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

@app.get("/")
async def root():
    return {
        "message": "3D Bin Packing API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/methods")
async def get_packing_methods():
    return {
        "methods": [method.value for method in PackingMethod]
    }

@app.get("/standard-boxes")
async def get_standard_boxes():
    return {"standard_boxes": STANDARD_BOXES}

@app.post("/pack", response_model=PackingResult)
async def create_packing_task(request: PackingRequest, background_tasks: BackgroundTasks):
    try:
        # Валидация данных
        validator = DataValidator()
        error_handler = APIErrorHandler()
        
        pallet_validation = validator.validate_pallet_data(request.pallet.dict())
        if not pallet_validation.is_valid:
            validation_errors = error_handler.format_validation_errors(pallet_validation)
            raise HTTPException(
                status_code=400, 
                detail=f"Ошибки в данных поддона: {validation_errors}"
            )
        
        boxes_data = [box.dict() for box in request.boxes]
        boxes_validation = validator.validate_boxes_list(boxes_data)
        if not boxes_validation.is_valid:
            validation_errors = error_handler.format_validation_errors(boxes_validation)
            raise HTTPException(
                status_code=400,
                detail=f"Ошибки в данных коробок: {validation_errors}"
            )
        
        task_id = str(uuid.uuid4())
        task = PackingResult(
            task_id=task_id,
            status="pending",
            created_at=datetime.now()
        )
        
        tasks_storage[task_id] = task
        background_tasks.add_task(perform_packing, task_id, request)
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

async def perform_packing(task_id: str, request: PackingRequest):
    try:
        tasks_storage[task_id].status = "processing"
        
        # Создание packer'а
        packer = create_packer(request.method, request.support_threshold, request.weight_check_enabled)
        
        # Добавление поддона - ИСПРАВЛЕНИЕ: приводим к int
        pallet = request.pallet
        packer.add_bin(Bin(
            'Поддон', 
            int(pallet.length), 
            int(pallet.width), 
            int(pallet.height), 
            float(pallet.max_weight)
        ))
        
        # Добавление коробок
        item_count = 0
        for box in request.boxes:
            for i in range(box.quantity):
                item_count += 1
                packer.add_item(Item(
                    f'{box.name}_{i}',
                    float(box.length),
                    float(box.width),
                    float(box.height),
                    float(box.weight)
                ))
        
        # Выполнение упаковки
        packer.pack()
        
        # Формирование результата
        result = format_packing_result(packer, item_count, request)
        
        tasks_storage[task_id].status = "completed"
        tasks_storage[task_id].result = result
        tasks_storage[task_id].completed_at = datetime.now()
        
    except Exception as e:
        tasks_storage[task_id].status = "failed"
        tasks_storage[task_id].error = str(e)
        tasks_storage[task_id].completed_at = datetime.now()

def create_packer(method: str, support_threshold: float, weight_check_enabled: bool):
    if method == PackingMethod.WEIGHT_AWARE.value:
        return WeightAwarePacker(support_threshold, weight_check_enabled)
    elif method == PackingMethod.EXTREME_POINTS.value:
        return ExtremePointPacker()
    elif method == PackingMethod.LAFF.value:
        return LAFFPacker()
    elif method == PackingMethod.CORNER_POINTS.value:
        return CornerPointPacker()
    elif method == PackingMethod.SFC.value:
        return SFCPacker()
    else:
        return WeightAwarePacker(support_threshold, weight_check_enabled)

def format_packing_result(packer, item_count: int, request: PackingRequest) -> Dict[str, Any]:
    packed_items = len(packer.bins[0].items)
    unpacked_items = len(packer.unpacked_items)
    
    # ИСПРАВЛЕНИЕ: безопасное приведение типов
    total_box_volume = sum(
        float(item.width) * float(item.height) * float(item.depth) 
        for item in packer.bins[0].items
    )
    bin_volume = (
        float(packer.bins[0].width) * 
        float(packer.bins[0].height) * 
        float(packer.bins[0].depth)
    )
    space_utilization = (total_box_volume / bin_volume) * 100 if bin_volume > 0 else 0
    
    packed_weight = sum(float(item.weight) for item in packer.bins[0].items)
    total_weight = sum(float(item.weight) for item in packer.items)
    
    return {
        "summary": {
            "total_items": item_count,
            "packed_items": packed_items,
            "unpacked_items": unpacked_items,
            "space_utilization": round(space_utilization, 2),
            "calculation_time": round(getattr(packer, 'calculation_time', 0), 3),
            "total_weight": round(total_weight, 2),
            "packed_weight": round(packed_weight, 2)
        },
        "packed_items": [
            {
                "name": item.name,
                "position": {"x": float(item.position[0]), "y": float(item.position[1]), "z": float(item.position[2])},
                "dimensions": {"width": float(item.width), "height": float(item.height), "depth": float(item.depth)},
                "weight": float(item.weight)
            }
            for item in packer.bins[0].items
        ],
        "unpacked_items": [
            {
                "name": item.name,
                "dimensions": {"width": float(item.width), "height": float(item.height), "depth": float(item.depth)},
                "weight": float(item.weight)
            }
            for item in packer.unpacked_items
        ]
    }

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    return {
        "task_id": task.task_id,
        "status": task.status,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "error": task.error
    }

@app.get("/result/{task_id}")
async def get_task_result(task_id: str):
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    
    if task.status == "pending" or task.status == "processing":
        raise HTTPException(status_code=202, detail="Задача еще выполняется")
    
    if task.status == "failed":
        raise HTTPException(status_code=500, detail=f"Задача завершилась с ошибкой: {task.error}")
    
    return task.result

@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    del tasks_storage[task_id]
    return {"message": "Задача удалена"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)