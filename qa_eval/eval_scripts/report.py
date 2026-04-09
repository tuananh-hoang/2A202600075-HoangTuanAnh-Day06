import pandas as pd
import os

# 1. Cấu hình đường dẫn (Thay tên file report của bạn vào đây)
csv_file = "qa_eval/test_cases/report/report_0409_2309.csv"
excel_output = csv_file.replace(".csv", "_final_report.xlsx")

if not os.path.exists(csv_file):
    print(f"❌ Không tìm thấy file: {csv_file}")
else:
    # 2. Đọc dữ liệu CSV
    df = pd.read_csv(csv_file, encoding='utf-8-sig')

    # 3. Xuất qua Excel dùng engine xlsxwriter (không cần openpyxl)
    # index=False để không lưu cột số thứ tự thừa của Pandas
    df.to_excel(excel_output, index=False, engine='xlsxwriter')
    
    # 4. Hiển thị báo cáo chuẩn hóa ngay trên màn hình (Pandas thuần)
    print("\n" + "="*60)
    print("📊 BÁO CÁO TỔNG HỢP (SUMMARY REPORT)")
    print("="*60)
    
    # Tính toán các chỉ số
    total = len(df)
    passed = len(df[df['Status'] == 'SUCCESS'])
    failed = total - passed
    pass_rate = (passed / total) * 100
    avg_sim = df['Similarity_Score'].mean()

    print(f"- Tổng số testcase:   {total}")
    print(f"- Số câu PASS:        {passed} ✅")
    print(f"- Số câu FAIL:        {failed} ❌")
    print(f"- Tỷ lệ thành công:   {pass_rate:.2f}%")
    print(f"- Điểm trung bình:    {avg_sim:.2f}%")
    
    print("\n📍 THỐNG KÊ THEO DANH MỤC (CATEGORY):")
    # Groupby để xem mảng nào đang yếu
    category_summary = df.groupby('Category').agg({
        'Status': lambda x: (x == 'SUCCESS').sum(),
        'Similarity_Score': 'mean'
    }).rename(columns={'Status': 'Pass_Count', 'Similarity_Score': 'Avg_Score'})
    
    print(category_summary)
    
    print("="*60)
    print(f"✅ Đã chuyển đổi thành công sang file Excel: \n{os.path.abspath(excel_output)}")