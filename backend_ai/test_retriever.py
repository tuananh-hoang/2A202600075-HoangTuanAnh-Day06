import os
from dotenv import load_dotenv

# Đảm bảo load biến môi trường trước khi import các module của app
load_dotenv()

from app.utils.vector_tools import CustomFAISSSQLiteRetriever
from app.core import config

def run_test():
    print("="*50)
    print(" BẮT ĐẦU TEST KẾT NỐI FAISS & SQLITE")
    print("="*50)
    
    # 1. Kiểm tra file có tồn tại không
    if not os.path.exists(config.FAISS_PATH):
        print(f"❌ LỖI: Không tìm thấy file FAISS tại: {config.FAISS_PATH}")
        return
    if not os.path.exists(config.SQLITE_PATH):
        print(f"❌ LỖI: Không tìm thấy file SQLite tại: {config.SQLITE_PATH}")
        return
        
    print(f"✅ Đã tìm thấy DB Data Pipeline: \n - {config.FAISS_PATH} \n - {config.SQLITE_PATH}\n")
    
    try:
        # 2. Khởi tạo Retriever (k=3 nghĩa là lấy 3 kết quả)
        print(f"⏳ Đang tải mô hình nhúng '{config.EMBEDDING_MODEL}' và FAISS index...")
        retriever = CustomFAISSSQLiteRetriever(k=3)
        print("✅ Khởi tạo Retriever thành công!\n")
        
        # 3. Đặt một câu hỏi thực tế
        test_query = "Quy định mang thú cưng lên xe Xanh SM như thế nào?"
        print(f"❓ Câu hỏi test: '{test_query}'\n")
        
        print("🔍 Đang truy xuất dữ liệu...")
        
        # Gọi thẳng hàm protected để lấy list of Documents
        # Truyền run_manager=None vì chạy test độc lập
        results = retriever._get_relevant_documents(test_query, run_manager=None)
        
        # 4. In kết quả
        if not results:
            print("⚠️ Không tìm thấy kết quả nào phù hợp.")
        else:
            print(f"✅ Tìm thấy {len(results)} đoạn văn bản liên quan:\n")
            for i, doc in enumerate(results):
                print(f"--- Kết quả {i+1} ---")
                print(f"📑 Nguồn (Metadata): {doc.metadata.get('source', 'Unknown')}")
                # Cắt bớt nội dung nếu quá dài để dễ nhìn
                content_preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                print(f"📄 Nội dung: {content_preview}\n")
                
    except Exception as e:
        print(f"❌ QUÁ TRÌNH TEST THẤT BẠI. Lỗi chi tiết:")
        print(str(e))

if __name__ == "__main__":
    run_test()