import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import uuid

# Используем предообученную модель для векторизации
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# --- Явно указываем путь для сохранения базы данных ---
# Определяем путь к директории, где находится этот скрипт (т.е. backend/)
script_dir = os.path.dirname(os.path.abspath(__file__))
# Путь для сохранения ChromaDB
db_path = os.path.join(script_dir, "chroma")

# Создаем клиент, который будет СОХРАНЯТЬ данные на диск в указанную папку
client = chromadb.PersistentClient(path=db_path)

# Создаем коллекцию для хранения векторов
# get_or_create_collection гарантирует, что коллекция будет создана, если ее нет
collection = client.get_or_create_collection(
    name="gsp_collection_with_metadata",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    ),
    # ЯВНО УКАЗЫВАЕМ ИСПОЛЬЗОВАТЬ КОСИНУСНУЮ МЕТРИКУ!
    # Это ключевое исправление.
    metadata={"hnsw:space": "cosine"}
)


def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=200):
    """
    Разделяет большой текст на более мелкие чанки.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = text_splitter.split_text(text)
    return chunks


def add_documents_to_collection(documents, metadatas):
    """
    Добавляет документы и их метаданные в коллекцию ChromaDB.
    """
    if not documents:
        return

    # Генерируем уникальные ID для каждого чанка, чтобы избежать дубликатов
    ids = [str(uuid.uuid4()) for _ in range(len(documents))]

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    print(f"  [+] Добавлено {len(documents)} чанков в коллекцию.")


def find_similar_documents(query, n_results=3, where_filter=None):
    """
    Ищет в коллекции документы, наиболее похожие на запрос.
    Позволяет фильтровать по метаданным с помощью where_filter.
    Возвращает кортеж: (список документов, список оценок схожести, список метаданных)
    """
    if where_filter is None:
        where_filter = {}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,  # Добавляем фильтрацию
        include=["documents", "distances", "metadatas"]  # Запрашиваем также и метаданные
    )
    
    if not results or not results["documents"]:
        return [], [], []

    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]
    scores = [1 - dist for dist in distances]
    
    return documents, scores, metadatas


def process_and_add_text(text, metadata):
    """
    Обрабатывает переданный текст, разделяет на чанки и добавляет в коллекцию
    вместе с метаданными.
    """
    try:
        chunks = split_text_into_chunks(text)
        # Каждый чанк получает одинаковые метаданные, так как они из одного файла
        chunk_metadatas = [metadata] * len(chunks)
        add_documents_to_collection(chunks, chunk_metadatas)
        print(f"  [*] Документ '{metadata.get('source', '')}' успешно обработан.")
        return True
    except Exception as e:
        print(f"  [!] Ошибка при обработке документа '{metadata.get('source', '')}': {e}")
        return False
