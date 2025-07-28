import os
import json
import shutil
import logging
from datetime import datetime
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
import torch
import time
from tqdm import tqdm
import chromadb

# .env 파일에서 환경 변수 로드 (backend 폴더 기준)
load_dotenv("../.env")

# 로깅 설정
def setup_logging():
    """로깅 설정"""
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일명 (현재 시간 포함)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"build_chromadb_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # 로거 설정
    logger = logging.getLogger('build_chromadb')
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러 (상세 로그)
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # 콘솔 핸들러 (간단한 로그)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filepath

# 로거 초기화
logger, log_filepath = setup_logging()

logger.info("=" * 60)
logger.info("ChromaDB 빌드 시작")
logger.info(f"로그 파일: {log_filepath}")
logger.info("=" * 60)

# 설정
JSON_DIR = "../datas/json_results"
CHROMA_DIR = "../datas/chroma_db"        # 저장할 Chroma DB 경로

# 임베딩 모델 설정 (환경 변수에서 가져오기)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")

# 디바이스 설정 - 따옴표 제거 및 검증
device_env = os.getenv("EMBEDDING_DEVICE", "")
logger.info(f"환경 변수 EMBEDDING_DEVICE: '{device_env}'")

if device_env:
    EMBEDDING_DEVICE = device_env.strip().strip("'\"")  # 따옴표 제거
    logger.info(f"따옴표 제거 후: '{EMBEDDING_DEVICE}'")
else:
    EMBEDDING_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"기본값 설정: '{EMBEDDING_DEVICE}'")

EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

logger.info(f"임베딩 모델 설정:")
logger.info(f"   - 모델: {EMBEDDING_MODEL_NAME}")
logger.info(f"   - 디바이스: {EMBEDDING_DEVICE}")
logger.info(f"   - 배치 크기: {EMBEDDING_BATCH_SIZE}")

# CUDA 사용 가능 여부 확인
if not torch.cuda.is_available():
    logger.error("❌ CUDA가 사용 불가능합니다.")
    logger.error("GPU 드라이버와 PyTorch CUDA 버전을 확인해주세요.")
    logger.error("프로그램을 종료합니다.")
    exit(1)

logger.info(f"✅ CUDA 사용 가능: {torch.cuda.get_device_name(0)}")

# JSON 폴더 확인
if not os.path.exists(JSON_DIR):
    logger.error(f"오류: JSON 폴더 '{JSON_DIR}'가 존재하지 않습니다.")
    logger.error("먼저 JSON 변환을 완료해주세요.")
    exit()

# 기존 Chroma DB 디렉토리가 있다면 삭제하고 새로 시작
if os.path.exists(CHROMA_DIR):
    logger.warning(f"⚠️ 기존 Chroma DB 디렉토리 '{CHROMA_DIR}'를 삭제합니다. (중복 방지)")
    shutil.rmtree(CHROMA_DIR) # 폴더와 그 안의 모든 내용을 삭제

# 임베딩 로딩 (CUDA 필수)
try:
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': EMBEDDING_DEVICE},
        encode_kwargs={'batch_size': EMBEDDING_BATCH_SIZE}
    )
    logger.info(f"✅ 임베딩 모델 로드 완료: {EMBEDDING_DEVICE}")
except RuntimeError as e:
    logger.error(f"❌ CUDA 디바이스 오류 발생: {e}")
    logger.error("CUDA가 필요합니다. GPU 드라이버와 PyTorch CUDA 버전을 확인해주세요.")
    logger.error("프로그램을 종료합니다.")
    exit(1)

# Document 목록 생성
all_documents = []
logger.info(f"\n�� JSON 파일 로딩 중...")

# nttSn 순서로 정렬하여 로드
json_files = []
for filename in os.listdir(JSON_DIR):
    if filename.endswith(".json"):
        try:
            # 파일명에서 nttSn 추출 (예: "13176_union.json" → 13176)
            nttsn = int(filename.split('_')[0])
            json_files.append((nttsn, filename))
        except (ValueError, IndexError) as e:
            logger.info(f"⚠️ 파일명 파싱 오류: {filename} - {e}")
            continue

# nttSn 순서로 정렬
json_files.sort(key=lambda x: x[0])

logger.info(f"총 {len(json_files)}개의 JSON 파일을 nttSn 순서로 로드합니다...")

# 정렬된 순서로 로드
for nttsn, filename in json_files:
    file_path = os.path.join(JSON_DIR, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for item in data:
                # metadata를 ChromaDB가 허용하는 형태로 평면화
                original_metadata = item["metadata"]
                flattened_metadata = {}
                
                # metadata 검증: 딕셔너리 값이 있는지 확인
                has_dict_value = False
                for key, value in original_metadata.items():
                    if isinstance(value, dict):
                        has_dict_value = True
                        logger.info(f"⚠️ 딕셔너리 값 발견: {filename} - {key}: {value}")
                        break
                
                if has_dict_value:
                    logger.info(f"❌ 건너뛰기: {filename} - 딕셔너리 값이 포함된 metadata")
                    continue
                
                # 중첩된 딕셔너리를 평면화
                for key, value in original_metadata.items():
                    if isinstance(value, dict):
                        # 중첩된 딕셔너리의 각 키-값을 평면화
                        for sub_key, sub_value in value.items():
                            flattened_metadata[f"{key}_{sub_key}"] = sub_value
                    else:
                        # 단순한 값은 그대로 사용
                        flattened_metadata[key] = value
                
                doc = Document(
                    page_content=item["text"],
                    metadata=flattened_metadata
                )
                all_documents.append(doc)
            logger.info(f"✅ 로드 완료: {filename} (nttSn: {nttsn}, {len(data)}개 항목)")
        except Exception as e:
            logger.info(f"❌ 오류 발생: {filename} - {e}")

logger.info(f"\n🔍 총 {len(all_documents)}개의 문서를 임베딩합니다...")

def create_chroma_with_progress(documents, embedding_model, persist_directory):
    """
    대용량 문서를 배치로 임베딩하고 ChromaDB에 저장하는 함수 (최신 방식)
    """
    # 1. ChromaDB 클라이언트 설정
    client = chromadb.PersistentClient(path=persist_directory)
    collection_name = "my_report_collection" # 컬렉션 이름 지정

    # 기존 컬렉션이 있다면 삭제
    if collection_name in [c.name for c in client.list_collections()]:
        client.delete_collection(name=collection_name)
    
    # 2. 임베딩 함수 없이 컬렉션 생성
    collection = client.create_collection(name=collection_name)

    # 3. 문서들을 배치로 나누어 처리 (메모리 관리)
    batch_size = EMBEDDING_BATCH_SIZE # 한 번에 처리할 문서 수, 시스템 메모리에 따라 조절
    
    logger.info(f"총 {len(documents)}개의 문서를 {batch_size}개씩 나누어 임베딩 및 저장합니다...")

    for i in tqdm(range(0, len(documents), batch_size), desc="ChromaDB에 저장 중"):
        batch_docs = documents[i:i+batch_size]
        
        # 문서 내용만 추출하여 임베딩
        batch_contents = [doc.page_content for doc in batch_docs]
        embeddings = embedding_model.embed_documents(batch_contents)
        
        # 메타데이터와 ID 준비
        metadatas = [doc.metadata for doc in batch_docs]
        ids = [f"id_{i+j}" for j in range(len(batch_docs))] # 고유 ID 생성
        
        # 4. 컬렉션에 데이터 추가
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=batch_contents # 원본 텍스트도 함께 저장
        )

    logger.info("✅ 모든 문서의 임베딩 및 저장이 완료되었습니다.")
    return collection

# 스크립트의 메인 부분에서 이 함수를 호출
create_chroma_with_progress(all_documents, embedding_model, CHROMA_DIR) 