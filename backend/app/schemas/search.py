from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 10
    search_results: Optional[List[Dict[str, Any]]] = None

class SearchResponse(BaseModel):
    query: str
    summary_query: str
    priority_sections: List[str]
    metadata_filters: Dict[str, str]
    intent: Optional[str] = None
    total_results: int
    results: List[Dict[str, Any]]
    usage_metadata: Optional[Dict[str, Any]] = None 