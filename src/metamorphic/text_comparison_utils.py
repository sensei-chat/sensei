from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def sequence_similarity(text1, text2):
    return SequenceMatcher(None, text1, text2).ratio()

def exact_similarity(text1, text2):
    if text1 == text2:
        return 1.0
    return 0.0

def jaccard_similarity(text1, text2):
    # Split the texts into sets of words
    set1 = set(text1.lower().split())
    set2 = set(text2.lower().split())

    # Calculate the Jaccard similarity
    intersection = set1.intersection(set2)
    union = set1.union(set2)

    return len(intersection) / len(union)

def tf_idf_cosine_similarity(text1, text2):
    # Convert the texts into TF-IDF vectors
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])

    # Compute cosine similarity
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return cosine_sim[0][0]