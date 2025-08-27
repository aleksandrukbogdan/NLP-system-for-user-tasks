from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import datetime
import logging
from collections import defaultdict

from database import find_similar_documents
from gigachat import get_gigachat_response

# --- Настройка логирования для нераспознанных запросов ---
# Определяем абсолютный путь к папке с логами для надежности
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "unrecognized_requests.log")

# Создаем логгер для нераспознанных запросов
unrecognized_logger = logging.getLogger('unrecognized')
unrecognized_logger.setLevel(logging.INFO)
# Создаем обработчик для записи в файл
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
# Создаем форматтер, чтобы в логе была дата и сам запрос
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
# Избегаем двойного добавления обработчика
if not unrecognized_logger.hasHandlers():
    unrecognized_logger.addHandler(file_handler)
# -----------------------------

# --- Отладочный Middleware для перехвата всех запросов ---
class DebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            print("="*30)
            print(f"DEBUG: Получен запрос: {request.method} {request.url.path}")
            print("DEBUG: Заголовки:")
            for name, value in request.headers.items():
                print(f"  -> {name}: {value}")
            print("="*30)
        
        await self.app(scope, receive, send)


app = FastAPI(
    title="GSP Keys Assistant API",
    description="Интеллектуальный ассистент для помощи сотрудникам.",
    version="1.0.0",
)

# --- Добавляем Middleware ---
# Сначала наш отладочный, чтобы он сработал первым
app.add_middleware(DebugMiddleware)

# Порог уверенности. Если схожесть лучшего документа ниже, считаем ответ неуверенным.
CONFIDENCE_THRESHOLD = 0.5 
# Порог релевантности. Если схожесть ЛУЧШЕГО документа ниже, считаем, что ничего не найдено.
SUGGESTION_THRESHOLD = 0.3 
# Категория для каталога ИТ-услуг (должна совпадать с именем папки)
IT_SERVICE_CATALOG_CATEGORY = "it_service_catalog"


# Настройка CORS
# Для отладки разрешаем все источники.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic модель для валидации входящего JSON
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    source: str = "Не определен"
    confident: bool = False
    suggestions: list[str] = []
    show_fallback_button: bool = False # Флаг для кнопки "Я не получил ответ"


# Директория для временного хранения загруженных файлов
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def filter_latest_documents(docs, metadatas):
    """
    Фильтрует список документов, оставляя только самые новые версии для каждого источника.
    """
    if not docs:
        return [], []

    latest_docs = {}
    for i, meta in enumerate(metadatas):
        source = meta.get("source")
        # Убедимся, что дата в правильном формате и сравнима
        load_date_str = meta.get("load_date")
        if not source or not load_date_str:
            continue
        
        load_date = datetime.datetime.fromisoformat(load_date_str)

        if source not in latest_docs or load_date > latest_docs[source]["date"]:
            latest_docs[source] = {"date": load_date, "doc": docs[i], "meta": meta}

    # Собираем отфильтрованные списки
    filtered_docs = [data["doc"] for data in latest_docs.values()]
    filtered_metadatas = [data["meta"] for data in latest_docs.values()]
    
    print(f"  [ИНФО] Фильтрация версий: из {len(docs)} документов оставлено {len(filtered_docs)} уникальных и самых новых.")
    
    return filtered_docs, filtered_metadatas


@app.post("/ask", response_model=QueryResponse, summary="Задать вопрос ассистенту")
async def ask_question(request: QueryRequest):
    """
    Принимает вопрос от пользователя и обрабатывает его по многоступенчатому сценарию:
    1. Поиск в ИТ-услугах.
    2. Поиск в базе знаний (памятки).
    3. Поиск в примерах заявок для маршрутизации.
    4. Ответ по-умолчанию с контактами поддержки.
    """
    query = request.query
    print(f"\n{'='*20}\nНОВЫЙ ЗАПРОС: '{query}'\n{'='*20}")

    # --- Шаг 1: Поиск в каталоге ИТ-услуг ---
    print(f"-> Шаг 1: Поиск в каталоге ИТ-услуг ('{IT_SERVICE_CATALOG_CATEGORY}')...")
    it_docs, it_scores, it_metadatas = find_similar_documents(
        query, n_results=1, where_filter={"category": IT_SERVICE_CATALOG_CATEGORY}
    )

    # Проверяем, что лучший результат хоть сколько-нибудь релевантен
    if it_docs and it_scores[0] >= SUGGESTION_THRESHOLD:
        # Фильтруем по последней версии
        it_docs, it_metadatas = filter_latest_documents(it_docs, it_metadatas)
        
        if it_docs and it_scores[0] >= CONFIDENCE_THRESHOLD:
            service_name = it_metadatas[0].get('service_name', 'услугу')
            source_file = it_metadatas[0].get("source", "Каталог ИТ-услуг")
            
            # Формируем уточняющий ответ
            answer = f"Похоже, вас интересует '{service_name}'. Я нашел информацию об этом в каталоге ИТ-услуг. Готовлю ответ..."
            
            # Получаем полный ответ от GigaChat на основе найденного контекста
            full_answer = get_gigachat_response(
                user_prompt=query,
                context_documents=it_docs,
                is_confident=True,
                found_in="it_catalog"
            )
            final_answer = f"{answer}\n\n---\n\n{full_answer}"
            
            return QueryResponse(answer=final_answer, source=source_file, confident=True, show_fallback_button=True)

    print("  [ИНФО] В каталоге ИТ-услуг точного ответа не найдено.")

    # --- Шаг 2: Поиск в остальной базе знаний (памятки) ---
    print(f"-> Шаг 2: Поиск в общей базе знаний (памятки)...")
    knowledge_docs, knowledge_scores, knowledge_metadatas = find_similar_documents(
        query, n_results=3, where_filter={
            "$and": [
                {"doc_type": {"$eq": "knowledge"}},
                {"category": {"$ne": IT_SERVICE_CATALOG_CATEGORY}}
            ]
        }
    )

    # Проверяем, что лучший результат хоть сколько-нибудь релевантен
    if knowledge_docs and knowledge_scores[0] >= SUGGESTION_THRESHOLD:
        # Фильтруем по последней версии
        knowledge_docs, knowledge_metadatas = filter_latest_documents(knowledge_docs, knowledge_metadatas)
        
        # Отбираем те, что прошли порог уверенности
        confident_docs = [knowledge_docs[i] for i, score in enumerate(knowledge_scores) if score >= CONFIDENCE_THRESHOLD]

        if confident_docs:
            print(f"  [УСПЕХ] Найдены релевантные документы в базе знаний.")
            source_file = knowledge_metadatas[0].get("source", "База знаний")
            answer = get_gigachat_response(
                user_prompt=query,
                context_documents=confident_docs,
                is_confident=True
            )
            return QueryResponse(answer=answer, source=source_file, confident=True, show_fallback_button=True)
        else:
            print("  [ИНФО] Уверенных ответов нет, но есть похожие темы. Предлагаем варианты.")
            # Для подсказок берем только те категории, что прошли минимальный порог
            relevant_metadatas = [knowledge_metadatas[i] for i, score in enumerate(knowledge_scores) if score >= SUGGESTION_THRESHOLD]
            suggestions = sorted(list(set(meta.get("category", "Без категории") for meta in relevant_metadatas if meta)))
            answer = "Я не нашел точного ответа, но, возможно, вас интересует одна из этих тем?"
            return QueryResponse(answer=answer, source="Предложены варианты", confident=False, suggestions=suggestions)

    print("  [ИНФО] В общей базе знаний ничего релевантного не найдено.")

    # --- Шаг 3: Попытка маршрутизации запроса ---
    print("-> Шаг 3: Поиск примеров для маршрутизации...")
    routing_docs, routing_scores, routing_metadatas = find_similar_documents(
        query, n_results=3, where_filter={"doc_type": "routing_example"}
    )
    
    # Проверяем, что лучший результат хоть сколько-нибудь релевантен
    if routing_docs and routing_scores[0] >= SUGGESTION_THRESHOLD:
        if routing_scores[0] >= 0.4: # Порог для маршрутизации можно оставить пониже
            department = routing_metadatas[0].get("department")
            if department:
                print(f"  [УСПЕХ] Запрос классифицирован. Направляется в отдел: '{department}'.")
                answer = get_gigachat_response(user_prompt=query, context_documents=[], is_confident=False, routing_info={"department": department})
                return QueryResponse(answer=answer, source=f"Маршрутизация в '{department}'", confident=True, show_fallback_button=True)
        else:
            print("  [ИНФО] Уверенной маршрутизации нет. Предлагаем варианты отделов.")
            # Для подсказок берем только те отделы, что прошли минимальный порог
            relevant_metadatas = [routing_metadatas[i] for i, score in enumerate(routing_scores) if score >= SUGGESTION_THRESHOLD]
            suggestions = sorted(list(set(meta.get("department", "Неизвестный отдел") for meta in relevant_metadatas if meta)))
            answer = "Я не смог точно определить нужный отдел. Возможно, ваш запрос следует направить в один из этих?"
            return QueryResponse(answer=answer, source="Предложены варианты маршрутизации", confident=False, suggestions=suggestions)

    print("  [ИНФО] Не удалось найти примеры для маршрутизации.")

    # --- Шаг 4: Если ничего не помогло ---
    print("-> Шаг 4: Ответ по умолчанию (контакты поддержки).")
    unrecognized_logger.info(query)
    answer = get_gigachat_response(query, [], is_confident=False)
    return QueryResponse(answer=answer, source="Не найдено", confident=False, show_fallback_button=False)


@app.post("/fallback", response_model=QueryResponse, summary="Обработка 'не получил ответ'")
async def fallback_response(request: QueryRequest):
    """
    Вызывается, когда пользователь нажимает кнопку 'Я не получил нужный ответ'.
    Логирует запрос и возвращает стандартный ответ с контактами поддержки.
    """
    query = request.query
    print(f"-> Fallback: Пользователь не удовлетворен ответом на запрос '{query}'.")
    unrecognized_logger.info(f"FALLBACK: {query}") # Делаем пометку, что это был fallback
    
    # Возвращаем стандартный ответ с контактами
    answer = get_gigachat_response(user_prompt="", context_documents=[], is_confident=False)
    return QueryResponse(answer=answer, source="Поддержка", confident=False, show_fallback_button=False)
