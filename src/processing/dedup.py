# import google.generativeai as genai
# import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity
# import os
# from dotenv import load_dotenv

# load_dotenv()
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# # Similarity threshold — articles above this are considered duplicates
# # 0.85 is a good starting point; lower = more aggressive dedup
# SIMILARITY_THRESHOLD = 0.85

# def get_embeddings(texts):
#     """
#     Calls Gemini text-embedding-004 for a list of texts.
#     Returns a numpy array of shape (len(texts), embedding_dim).

#     We batch all texts in one call to minimize API round-trips.
#     Gemini's embedding endpoint accepts a list directly.
#     """
#     result = genai.embed_content(
#         model="models/gemini-embedding-001",
#         content=texts,
#         task_type="SEMANTIC_SIMILARITY",
#     )
#     # result["embedding"] is a list of vectors (list of lists)
#     return np.array(result["embedding"])

# def deduplicate_articles(articles):
#     """
#     Removes near-duplicate articles based on title similarity.
#     Keeps the first occurrence (earlier in the list = higher priority feed).
#     Returns the deduplicated list.
#     """
#     if not articles:
#         return articles

#     titles = [a["title"] for a in articles]
    
#     print(f"[Dedup] Computing embeddings for {len(titles)} articles...")
#     embeddings = get_embeddings(titles)

#     # Compute full pairwise cosine similarity matrix
#     # Shape: (n_articles, n_articles)
#     sim_matrix = cosine_similarity(embeddings)

#     # Greedy dedup: iterate in order, mark duplicates of already-kept articles
#     kept = []
#     duplicate_indices = set()

#     for i in range(len(articles)):
#         if i in duplicate_indices:
#             continue  # already marked as a duplicate, skip it

#         kept.append(articles[i])

#         # Mark everything after i that's too similar as a duplicate
#         for j in range(i + 1, len(articles)):
#             if sim_matrix[i][j] >= SIMILARITY_THRESHOLD:
#                 duplicate_indices.add(j)

#     removed = len(articles) - len(kept)
#     print(f"[Dedup] Removed {removed} duplicates. {len(kept)} articles remaining.")
#     return kept









from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.80

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def deduplicate_articles(articles):
    if not articles:
        return articles

    kept = []

    for article in articles:
        title = article["title"]
        is_duplicate = False

        for kept_article in kept:
            if similar(title, kept_article["title"]) >= SIMILARITY_THRESHOLD:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(article)

    removed = len(articles) - len(kept)
    print(f"[Dedup] Removed {removed} duplicates. {len(kept)} articles remaining.")
    return kept