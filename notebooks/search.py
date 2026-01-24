from elasticsearch import Elasticsearch

# -----------------------
# Connect to ES 8.x server
# -----------------------
es_client = Elasticsearch(
    "http://localhost:9200",
    request_timeout=30
)


from qdrant_client import QdrantClient, models

# Initialize Qdrant client
qd_client = QdrantClient("http://localhost:6333")
from sentence_transformers import SentenceTransformer

# Initialize
model_handle = SentenceTransformer("BAAI/bge-large-en-v1.5")



def elastic_search(query):
    """
    Runs the same search query on:
      - collection-new
      - collection-old
      - collection-map
    Returns combined results from all three.
    """

    # --- Search 1: collection-new ---
    search_new = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "text^3",
                            "metadata.section_title",
                            "metadata.section_number",
                            "metadata.law_name"
                        ],
                        "type": "best_fields"
                    }
                }]
            }
        }
    }
    resp_new = es_client.search(index="collection-new", query=search_new["query"], size=search_new["size"])
    results_new = [hit["_source"] for hit in resp_new["hits"]["hits"]]

    # --- Search 2: collection-old ---
    search_old = {
        "size": 5,
        "query": {
            "bool": {
                "must": [{
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "text^3",
                            "metadata.section_title",
                            "metadata.section_number",
                            "metadata.law_name"
                        ],
                        "type": "best_fields"
                    }
                }]
            }
        }
    }
    resp_old = es_client.search(index="collection-old", query=search_old["query"], size=search_old["size"])
    results_old = [hit["_source"] for hit in resp_old["hits"]["hits"]]

    search_map = {
        "size": 5,
        "query": {
            "bool": {
                "must": [{
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "fields.New_Law_Section^3",
                            "fields.Old_Law_Section^3",
                            "fields.Subject",
                            "fields.Summary_of_comparison"
                        ],
                        "type": "best_fields"
                    }
                }]
            }
        }
    }
    resp_map = es_client.search(index="collection-map", query=search_map["query"], size=search_map["size"])
    results_map = [hit["_source"] for hit in resp_map["hits"]["hits"]]

    # --- Combined results ---
    combined_results = {
        "collection-new": results_new,
        "collection-old": results_old,
        "collection-map": results_map  # key updated here
    }

    return combined_results




def vector_search(question):
    if not question:
        question = " "  # fallback for empty query

    # Generate embedding
    vector = list(model_handle.encode([question]))[0]

    # Define which collections to search and limits
    search_config = [
        ("collection-new", 10),
        ("collection-old", 5),
        ("collection-map", 5)
    ]

    results = {}

    for col_name, limit in search_config:
        # ✅ Using query_points (returns object with .points)
        query_points = qd_client.query_points(
            collection_name=col_name,
            query=vector,
            limit=limit,
            with_payload=True
        )

        cleaned_results = []

        for p in query_points.points:
            payload = p.payload or {}

            if col_name == "collection-map":
                fields = payload.get("fields", {})
                cleaned_results.append({
                    "chunk_id": payload.get("chunk_id"),
                    "source_file": payload.get("source_file"),
                    "New_Law_Section": fields.get("New_Law_Section"),
                    "Old_Law_Section": fields.get("Old_Law_Section"),
                    "Subject": fields.get("Subject"),
                    "Summary_of_comparison": fields.get("Summary_of_comparison"),
                })
            else:
                meta = payload.get("metadata", {}) or {}
                cleaned_results.append({
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "text": payload.get("content"),
                    "section_number": meta.get("section_number"),
                    "section_title": meta.get("section_title"),
                    "law_name": meta.get("law_name"),
                })

        results[col_name] = cleaned_results

    return results





import numpy as np

def hybrid_search(question, alpha=0.3):
    """
    Hybrid search:
    1. Get chunks from vector_search
    2. Fetch embeddings from Qdrant for each chunk
    3. Combine with ElasticSearch scores
    4. Compute hybrid_score = alpha*_score + (1-alpha)*vector_score
    5. Remove duplicates and return top-k per collection
    """

    if not question:
        question = " "

    # --- Step 1: Generate query embedding ---
    query_vector = list(model_handle.encode([question]))[0]

    # --- Step 2: Get ElasticSearch results ---
    es_results = elastic_search(question)

    # --- Step 3: Get chunks from vector_search (without embeddings) ---
    vector_chunks = vector_search(question)

    # --- Step 4: Collection config (top-k per collection) ---
    search_config = [
        ("collection-new", 10),
        ("collection-old", 5),
        ("collection-map", 5)
    ]

    hybrid_results = {}

    for collection, top_k in search_config:
        combined = []
        seen_ids = set()

        # --- Add ElasticSearch results ---
        for r in es_results.get(collection, []):
            chunk_id = r.get("chunk_id") or r.get("doc_id")
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            combined.append({
                **r,
                "hybrid_score": alpha * r.get("_score", 1.0)
            })

        # --- Fetch embeddings from Qdrant for each chunk ---
        for r in vector_chunks.get(collection, []):
            chunk_id = r.get("chunk_id") or r.get("doc_id")
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)

            # Fetch embedding from Qdrant
            try:
                point = qd_client.retrieve(
                    collection_name=collection,
                    ids=[chunk_id],
                    with_vector=True
                )
                stored_vector = point[0].vector if point else None
            except Exception:
                stored_vector = None

            # Compute cosine similarity
            vector_score = 0.0
            if stored_vector:
                v1 = np.array(query_vector)
                v2 = np.array(stored_vector)
                vector_score = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))

            combined.append({
                **r,
                "hybrid_score": (1 - alpha) * vector_score
            })

        # --- Sort and keep top-k ---
        combined.sort(key=lambda x: x['hybrid_score'], reverse=True)
        hybrid_results[collection] = combined[:top_k]

    return hybrid_results
    



