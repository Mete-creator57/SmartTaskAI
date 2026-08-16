import os
import time
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai

load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

app = FastAPI(title="SmartTask AI Server")

class DecomposeRequest(BaseModel):
    task_title: str

class PlanDayRequest(BaseModel):
    tasks: List[str]

@app.get("/")
def home():
    return {"status": "ok", "message": "SmartTask AI Server is running!"}

@app.post("/api/decompose")
def decompose_task(req: DecomposeRequest):
    if not client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY не настроен")

    print(f"\n📩 [ДЕКОМПОЗИЦИЯ]: '{req.task_title}'")
    start_time = time.time()
    prompt = (
        f"Разбей задачу '{req.task_title}' на 3-4 конкретных коротких подзадачи на русском языке. "
        "Каждое действие должно занимать 10-15 минут. "
        "Ответь ТОЛЬКО списком шагов, каждый с новой строки, без цифр и тире."
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        lines = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
        print(f"✅ Успешно за {round(time.time() - start_time, 2)} сек ({len(lines)} шагов)")
        return {"task": req.task_title, "subtasks": lines}
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/plan-day")
def plan_day(req: PlanDayRequest):
    """НОВЫЙ ЭНДПОИНТ: Составление расписания дня"""
    if not client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY не настроен")

    print(f"\n🧠 [AI ПЛАНИРОВАНИЕ ДНЯ]: Получено {len(req.tasks)} задач")
    start_time = time.time()
    
    tasks_list_str = "\n".join(f"- {t}" for t in req.tasks)
    prompt = (
        "Ты профессиональный коуч по личной продуктивности. "
        f"Вот список задач человека на сегодня:\n{tasks_list_str}\n\n"
        "Составь оптимальный, реалистичный план дня с таймингом (например, 09:00 - 10:30, перерыв и т.д.) "
        "и дай 1 главный совет, как не выгореть. Напиши кратко, красиво, с эмодзи."
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        print(f"✅ План дня сгенерирован за {round(time.time() - start_time, 2)} сек")
        return {"plan": response.text.strip()}
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))