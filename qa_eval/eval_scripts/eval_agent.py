import os
import json
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from tools import evaluate_semantic_similarity, verify_data_accuracy

# Tự động xác định đường dẫn gốc
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '../.env'))

class XanhSMEvalAgent:
    def __init__(self):
        self.results = []
        # Cập nhật url backend
        self.backend_url = "http://10.45.194.84:8501/chat" 

    def call_bot_api(self, question):
        """Gọi API thực tế từ Backend và bắt lỗi kết nối"""
        try:
            # Gửi request với timeout 20s để tránh chờ đợi quá lâu nếu server treo
            response = requests.post(self.backend_url, json={"query": question}, timeout=20)
            response.raise_for_status()
            data = response.json()
            return data.get('answer', "Error: API response missing 'answer' key")
        except Exception as e:
            return f"Error: Connection failed ({str(e)})"

    def run_suite(self, file_path):
        """Chạy bộ kiểm định từ file JSON"""
        if not os.path.exists(file_path):
            print(f"❌ Không tìm thấy file dữ liệu tại: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            cases = json.load(f)

        print(f"🚀 Bắt đầu kiểm định {len(cases)} câu hỏi từ bộ dữ liệu chuẩn...\n")

        for case in cases:
            tc_id = case.get('id', 'N/A')
            category = case.get('category', 'General')
            q = case['question']
            expected = case['expected_answer']
            source = case.get('source', 'Unknown')
            
            # 1. Lấy câu trả lời thực tế từ Chatbot
            actual = self.call_bot_api(q)

            # In kết quả ra màn hình để theo dõi trực tiếp
            print(f"{'='*50}")
            print(f"🆔 ID: {tc_id} | [{category}]")
            print(f"❓ Q: {q}")
            print(f"🤖 Bot: {actual}")

            # 2. Kiểm tra độ chính xác dữ liệu (Số liệu, ngày tháng...)
            fact_result = verify_data_accuracy(actual, expected)
            is_fact_ok = fact_result['numbers_match']

            # 3. Kiểm tra độ tương đồng ngữ nghĩa (Dùng model AI offline)
            sim_result = evaluate_semantic_similarity(actual, expected)
            score = max(0.0, sim_result['score']) # Đảm bảo không bị điểm âm
            verdict = sim_result['verdict']

            # 4. Đánh giá tổng hợp
            final_status = "SUCCESS" if (is_fact_ok and verdict == "PASS") else "FAILED"
            
            # Ghi chú lý do nếu thất bại
            fail_reason = ""
            if not is_fact_ok:
                fail_reason = "Sai số liệu/thông tin định lượng. "
            if verdict == "FAIL":
                fail_reason += f"Ngữ nghĩa không đạt (Dưới 80%)."
            if "Error:" in actual:
                fail_reason = "Lỗi kết nối API hoặc Server Backend."

            print(f"📊 Score: {score}% | Fact: {'✅ OK' if is_fact_ok else '❌ SAI'}")
            print(f"🚩 Kết luận: {final_status}")

            self.results.append({
                "ID": tc_id,
                "Category": category,
                "Question": q,
                "Bot_Reply": actual,
                "Expected_Answer": expected,
                "Similarity_Score": score,
                "Fact_Match": is_fact_ok,
                "Status": final_status,
                "Fail_Reason": fail_reason,
                "Source": source
            })

    def export(self):
        """Xuất kết quả ra file CSV để làm báo cáo"""
        if not self.results:
            print("⚠️ Không có dữ liệu để xuất báo cáo.")
            return

        df = pd.DataFrame(self.results)
        
        # Tạo thư mục logs nếu chưa có
        log_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "test_cases", "logs"))
        os.makedirs(log_dir, exist_ok=True)
        
        # Đặt tên file theo thời gian hiện tại
        filename = f"report_eval_{datetime.now().strftime('%m%d_%H%M')}.csv"
        log_path = os.path.join(log_dir, filename)
        
        # Lưu file với chuẩn utf-8-sig để đọc được tiếng Việt trong Excel
        df.to_csv(log_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ KIỂM ĐỊNH HOÀN TẤT!")
        print(f"📍 Báo cáo chi tiết đã lưu tại: {log_path}")

if __name__ == "__main__":
    agent = XanhSMEvalAgent()
    
    # Xác định đường dẫn file JSON chứa các câu hỏi test
    DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "golden_datasets", "testcases.json"))
    
    try:
        agent.run_suite(DATA_PATH)
    except KeyboardInterrupt:
        print("\n🛑 Người dùng đã dừng chương trình.")
    except Exception as e:
        print(f"\n💥 Lỗi không xác định: {e}")
    finally:
        # Luôn xuất báo cáo dù có lỗi xảy ra giữa chừng
        agent.export()