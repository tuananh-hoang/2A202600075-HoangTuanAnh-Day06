import os
import re
from sentence_transformers import SentenceTransformer
from metrics import compute_cosine_similarity

# Khởi tạo model nhúng (Download về máy trong lần đầu chạy)
# Giải thích: Đây là model đa ngôn ngữ, rất mạnh về việc hiểu ý nghĩa câu tiếng Việt.
embeddings_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def evaluate_semantic_similarity(bot_response: str, expected_answer: str):
    """
    TOOL 1: So sánh độ tương đồng ngữ nghĩa.
    Sử dụng khi cần kiểm tra xem Bot có trả lời đúng ý hay không (văn phong).
    Input: bot_response (str), expected_answer (str)
    Output: {score: float, verdict: str}
    """
    v_bot = embeddings_model.encode(bot_response)
    v_truth = embeddings_model.encode(expected_answer)
    raw_score = compute_cosine_similarity(v_bot, v_truth)
    final_score = round(float(raw_score) * 100, 2)
    return {
        "score": final_score,
        "verdict": "PASS" if final_score >= 80 else "FAIL"
    }

def verify_data_accuracy(bot_response: str, expected_answer: str):
    """
    TOOL 2: Kiểm tra chính xác các con số.
    Sử dụng để đảm bảo các thông tin như giá cước, km không bị Bot bịa ra.
    Input: bot_response (str), expected_answer (str)
    Output: {numbers_match: bool}
    """
    bot_nums = set(re.findall(r'\d+', bot_response))
    truth_nums = set(re.findall(r'\d+', expected_answer))
    if not truth_nums:
        return {"numbers_match": True}
    # Bot phải chứa toàn bộ các số có trong đáp án chuẩn
    return {"numbers_match": truth_nums.issubset(bot_nums)}