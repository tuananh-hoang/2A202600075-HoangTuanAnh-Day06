import os
import json
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from tools import evaluate_semantic_similarity, verify_data_accuracy

# Xác định đường dẫn gốc và nạp biến môi trường
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#load_dotenv(os.path.join(BASE_DIR, '../.env'))

class XanhSMEvalAgent:
    def __init__(self):
        self.results = []
        # URL Backend của đồng đội bạn
        self.backend_url = "http://localhost:8000/chat" 

    def call_bot_api(self, question):
        """Gửi câu hỏi sang Backend và bắt lỗi mạng"""
        try:
            response = requests.post(self.backend_url, json={"message": question}, timeout=20)
            response.raise_for_status()
            data = response.json()
            return data.get('reply', "Error: No answer key")
        except Exception as e:
            # Nếu lỗi, trả về chuỗi bắt đầu bằng chữ Error:
            return f"Error: Connection failed ({str(e)})"

    def run_suite(self, file_path):
        """Luồng kiểm định chính"""
        if not os.path.exists(file_path):
            print(f"❌ Không tìm thấy file: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            cases = json.load(f)

        print(f"🚀 Bắt đầu chấm điểm {len(cases)} câu hỏi...\n")

        for case in cases:
            tc_id = case.get('id', 'N/A')
            category = case.get('category', 'General')
            q = case['question']
            expected = case['expected_answer']
            
            # 1. Lấy câu trả lời thực tế
            actual = self.call_bot_api(q)

            print(f"{'='*50}")
            print(f"🆔 ID: {tc_id} | ❓ Q: {q}")
            print(f"🤖 Bot: {actual}")

            # 2. Xử lý Logic chấm điểm (Phân tầng)
            if "Error:" in actual:
                # Nếu lỗi kết nối, ép tất cả về 0, không cho AI chấm điểm ảo
                score = 0.0
                is_fact_ok = False
                verdict = "FAIL"
                fail_reason = "Lỗi kết nối không lấy được câu trả lời."
            else:
                # Nếu kết nối OK, tiến hành chấm điểm thật
                # Kiểm tra số liệu
                fact_result = verify_data_accuracy(actual, expected)
                is_fact_ok = fact_result['numbers_match']

                # Kiểm tra ngữ nghĩa (Similarity)
                sim_result = evaluate_semantic_similarity(actual, expected)
                score = max(0.0, sim_result['score'])
                verdict = sim_result['verdict']
                
                # Phân tích lý do thất bại
                fail_reason = ""
                if not is_fact_ok:
                    fail_reason += "Sai số liệu thực tế. "
                if verdict == "FAIL":
                    fail_reason += f"Ngữ nghĩa chưa đạt (Chỉ đạt {score}%)."

            # 3. Chốt trạng thái cuối cùng
            final_status = "SUCCESS" if (is_fact_ok and verdict == "PASS") else "FAILED"
            
            print(f"📊 Score: {score}% | Fact: {'✅' if is_fact_ok else '❌'}")
            print(f"🚩 Trạng thái: {final_status}")

            self.results.append({
                "ID": tc_id,
                "Category": category,
                "Question": q,
                "Bot_Reply": actual,
                "Expected": expected,
                "Similarity_Score": score,
                "Fact_Match": is_fact_ok,
                "Status": final_status,
                "Reason": fail_reason if final_status == "FAILED" else "Đạt yêu cầu"
            })

    def export(self):
        """Xuất báo cáo CSV"""
        if not self.results:
            return

        df = pd.DataFrame(self.results)
        log_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "test_cases", "report"))
        os.makedirs(log_dir, exist_ok=True)
        
        path = os.path.join(log_dir, f"report_{datetime.now().strftime('%m%d_%H%M')}.csv")
        df.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"\n✅ BÁO CÁO HOÀN TẤT: {path}")

if __name__ == "__main__":
    agent = XanhSMEvalAgent()
    DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "golden_datasets", "testcases.json"))
    
    try:
        agent.run_suite(DATA_PATH)
    finally:
        agent.export()