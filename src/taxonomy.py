from __future__ import annotations


STRONG_TARGET_TITLES = (
    "recommendation systems engineer",
    "recommender systems engineer",
    "search engineer",
    "ranking engineer",
    "machine learning engineer",
    "ml engineer",
    "applied ml engineer",
    "ai engineer",
    "nlp engineer",
    "information retrieval engineer",
    "retrieval engineer",
    "data scientist",
    "ml platform engineer",
)

ADJACENT_ENGINEERING_TITLES = (
    "software engineer",
    "backend engineer",
    "data engineer",
    "full stack developer",
    "platform engineer",
    "devops engineer",
    "cloud engineer",
    "analytics engineer",
)

WRONG_ROLE_TITLES = (
    "marketing manager",
    "marketing associate",
    "digital marketing associate",
    "hr manager",
    "operations manager",
    "accountant",
    "customer support",
    "sales executive",
    "graphic designer",
    "civil engineer",
    "mechanical engineer",
    "content writer",
    "business analyst",
    "project manager",
)

CORE_RETRIEVAL_RANKING_TERMS = (
    "ranking",
    "ranker",
    "learning to rank",
    "ltr",
    "search relevance",
    "search ranking",
    "recommendation system",
    "recommendation systems",
    "recommender system",
    "recommender systems",
    "retrieval",
    "information retrieval",
    "semantic search",
    "hybrid search",
    "vector search",
    "embedding search",
    "candidate matching",
    "matching system",
    "reranking",
    "re-ranking",
    "relevance model",
    "discovery feed",
    "search product",
)

EMBEDDING_VECTOR_TERMS = (
    "embeddings",
    "embedding model",
    "sentence transformers",
    "bge",
    "e5",
    "faiss",
    "pinecone",
    "weaviate",
    "qdrant",
    "milvus",
    "elasticsearch",
    "opensearch",
    "bm25",
    "ann index",
    "vector database",
    "vector db",
    "index refresh",
    "embedding drift",
)

EVALUATION_TERMS = (
    "ndcg",
    "mrr",
    "map",
    "precision@k",
    "recall@k",
    "offline evaluation",
    "online evaluation",
    "offline-online correlation",
    "a/b test",
    "ab test",
    "relevance labels",
    "relevance judgment",
    "human judgments",
    "click-through",
    "ctr",
    "conversion",
    "dwell time",
)

PRODUCTION_EVIDENCE_TERMS = (
    "shipped",
    "deployed",
    "production",
    "real users",
    "scale",
    "latency",
    "monitoring",
    "regression",
    "pipeline",
    "data quality",
    "user behavior",
    "engagement",
    "experiment",
    "rollout",
    "owned",
    "migrated",
    "improved",
    "revenue-per-search",
    "offline metrics",
    "online metrics",
)

PRODUCT_COMPANY_INDUSTRIES = (
    "ai/ml",
    "software",
    "fintech",
    "e-commerce",
    "food delivery",
    "transportation",
    "saas",
    "marketplace",
    "consumer internet",
    "hr-tech",
    "recruiting tech",
)

SERVICE_COMPANY_NAMES = (
    "tcs",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "tech mahindra",
    "mindtree",
)

WEAK_AI_HYPE_TERMS = (
    "langchain",
    "openai api",
    "chatgpt",
    "prompt engineering",
    "rag side project",
    "ai tools",
    "genai enthusiast",
    "llm tutorial",
    "chatbot demo",
)

NON_TARGET_AI_SPECIALTIES = (
    "computer vision",
    "image classification",
    "object detection",
    "yolo",
    "speech recognition",
    "tts",
    "robotics",
    "gan",
    "gans",
)

PREFERRED_LOCATIONS = (
    "pune",
    "noida",
)

ACCEPTABLE_LOCATIONS = (
    "hyderabad",
    "mumbai",
    "delhi",
    "delhi ncr",
    "gurgaon",
    "gurugram",
    "bangalore",
    "bengaluru",
    "chennai",
)

EDUCATION_SIGNAL_FIELDS = (
    "computer science",
    "machine learning",
    "artificial intelligence",
    "data science",
    "information technology",
    "statistics",
    "mathematics",
)


def all_terms() -> set[str]:
    groups = (
        STRONG_TARGET_TITLES,
        ADJACENT_ENGINEERING_TITLES,
        WRONG_ROLE_TITLES,
        CORE_RETRIEVAL_RANKING_TERMS,
        EMBEDDING_VECTOR_TERMS,
        EVALUATION_TERMS,
        PRODUCTION_EVIDENCE_TERMS,
        PRODUCT_COMPANY_INDUSTRIES,
        SERVICE_COMPANY_NAMES,
        WEAK_AI_HYPE_TERMS,
        NON_TARGET_AI_SPECIALTIES,
        PREFERRED_LOCATIONS,
        ACCEPTABLE_LOCATIONS,
        EDUCATION_SIGNAL_FIELDS,
    )
    return {term.lower() for group in groups for term in group}
