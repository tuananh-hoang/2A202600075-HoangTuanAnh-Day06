from sklearn.metrics.pairwise import cosine_similarity

def compute_cosine_similarity(v1, v2):
    """
    Tính toán khoảng cách Cosine giữa 2 vector.
    Trả về: float (0.0 -> 1.0)
    """
    return cosine_similarity([v1], [v2])[0][0]