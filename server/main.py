import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai

# Загружаем переменные из .env
load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Инициализируем клиента Gemini
client = None
if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)

# Создаем приложение FastAPI
app = FastAPI(title="SmartTask AI Server")

# Модель входящих данных
class DecomposeRequest(BaseModel):
    task_title: str

@app.get("/")
def home():
    return {"status": "ok", "message": "SmartTask AI Server is running!"}

@app.post("/api/decompose")
def decompose_task(req: DecomposeRequest):
    """Эндпоинт разбиения задачи с помощью нейросети Gemini"""
    if not client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY не настроен в .env")

    prompt = (
        f"Разбей задачу '{req.task_title}' на 3-4 конкретных коротких подзадачи на русском языке. "
        "Каждое действие должно занимать 10-15 минут. "
        "Ответь ТОЛЬКО списком шагов, каждый с новой строки, без цифр, без тире и без вводных слов."
    )

    try:
        # Отправляем запрос к быстрой бесплатной модели Gemini 2.0 Flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        # Разбиваем ответ на список строк
        lines = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
        return {"task": req.task_title, "subtasks": lines}

    except Exception as e:
        print(f"\n❌ ПОДРОБНАЯ ОШИБКА: {e}\n")
        raise HTTPException(status_code=500, detail=f"Ошибка Gemini API: {str(e)}")