from playwright.sync_api import sync_playwright
import time
import os

# --- 1. HÀM CÀO DỮ LIỆU BẰNG PLAYWRIGHT ---
def crawl_xanhsm_policies():
    url = "https://www.xanhsm.com/terms-policies/general"
    data = []

    print(f"Bắt đầu truy cập: {url}")
    with sync_playwright() as p:
        # Chạy trình duyệt ẩn (headless=True)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, timeout=60000)

        # Đợi các thẻ question load xong
        page.wait_for_selector('div[id^="question-"]')
        
        # Lấy tất cả các block câu hỏi
        questions = page.locator('div[id^="question-"]')
        count = questions.count()
        print(f"Tìm thấy {count} mục quy định. Bắt đầu xử lý...")

        for i in range(count):
            q = questions.nth(i)
            
            # Lấy tiêu đề
            title = q.locator('span.text-left').inner_text().strip()
            
            # Lấy nút bấm để kiểm tra trạng thái đóng/mở
            button = q.locator('button')
            state = button.get_attribute('data-state')
            
            # NẾU ĐANG ĐÓNG -> CLICK ĐỂ MỞ RA LẤY TEXT
            if state == 'closed':
                button.click()
                page.wait_for_timeout(600)  # Đợi 0.6s cho hiệu ứng trượt (accordion) mở hẳn ra
            
            # Lấy nội dung bên trong
            content = q.locator('div[role="region"]').inner_text().strip()
            
            data.append({
                "title": title,
                "content": content
            })
            print(f"Đã cào xong: {title} (Độ dài: {len(content)} ký tự)")

        browser.close()
    return data

# --- 2. HÀM LƯU VÀO MARKDOWN ---
def save_to_markdown(data, folder_path="data_pipeline/raw_data"):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    print(f"\nBắt đầu lưu {len(data)} mục ra thư mục {folder_path}...")
    
    for i, item in enumerate(data):
        # Tạo tên file an toàn (bỏ ký tự đặc biệt)
        safe_title = "".join([c for c in item['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        safe_title = safe_title.replace(" ", "_").lower()
        filename = f"{i+1}_{safe_title}.md"
        filepath = os.path.join(folder_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Thêm title làm Heading 1
            f.write(f"# {item['title']}\n\n")
            f.write(item['content'])
            
        print(f"Đã lưu file: {filename}")
        
    print("Hoàn tất xuất file Markdown!")

if __name__ == "__main__":
    scraped_data = crawl_xanhsm_policies()
    if scraped_data:
        save_to_markdown(scraped_data)