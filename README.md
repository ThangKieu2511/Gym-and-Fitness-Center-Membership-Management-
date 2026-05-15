# 🏋️‍♂️ GymTK — Gym Management System

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![PySide6](https://img.shields.io/badge/Framework-PySide6-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)
![OpenCV](https://img.shields.io/badge/Feature-QR_Checkin-orange.svg)

**GymTK** là ứng dụng quản lý phòng gym hiện đại, được xây dựng bằng Python và PySide6. Ứng dụng hỗ trợ quản lý hội viên, đăng ký gói tập và tự động hóa quy trình check-in thông qua công nghệ quét mã QR thời gian thực.

---

## ✨ Tính năng chính

### 1. Dashboard & Thống kê
* **Tổng quan:** Hiển thị nhanh các chỉ số quan trọng (Tổng hội viên, Doanh thu tháng, Lượt tập hôm nay).
* **Biểu đồ trực quan:** Tích hợp Matplotlib để vẽ biểu đồ Donut (tỷ lệ gói tập) và biểu đồ cột (Top 5 hội viên năng nổ nhất).
* **Báo cáo:** Xuất danh sách hội viên sắp hết hạn ra file Excel với định dạng chuyên nghiệp.

### 2. Quản lý Hội viên (Member Management)
* **CRUD đầy đủ:** Thêm mới, cập nhật thông tin và xóa hội viên.
* **Hồ sơ hình ảnh:** Chụp ảnh trực tiếp từ Webcam hoặc tải ảnh lên để nhận diện hội viên.
* **Tìm kiếm thông minh:** Sử dụng kỹ thuật *Debounce Search* để tìm kiếm mượt mà, giảm tải cho Database.

### 3. Hệ thống Gói tập (Subscriptions)
* Quản lý các loại gói tập (Học sinh/Sinh viên, Người lớn).
* Tự động tính toán ngày bắt đầu và ngày kết thúc.
* Theo dõi trạng thái gói tập (Còn hạn/Hết hạn) theo thời gian thực.

### 4. QR Check-in tự động
* **Background Scanning:** Hệ thống quét QR chạy ngầm liên tục, người dùng không cần thao tác thủ công.
* **Nhận diện nhanh:** Tự động truy xuất thông tin hội viên ngay khi phát hiện mã QR hợp lệ.
---

## 🛠 Công nghệ sử dụng

* **Ngôn ngữ:** Python
* **Giao diện (GUI):** PySide6 (Qt for Python)
* **Cơ sở dữ liệu:** SQLite (truy vấn qua SQL thuần)
* **Thị giác máy tính:** OpenCV & PyZbar
* **Xử lý dữ liệu & Báo cáo:** Matplotlib, Pandas, Openpyxl

---

## 📂 Cấu trúc thư mục

```text
GymTK/
├── controllers/              # Xử lý logic nghiệp vụ (Business Logic)
│   ├── checkin_controller.py
│   ├── dashboard_controller.py
│   ├── member_controller.py
│   ├── qr_controller.py
│   └── subscription_controller.py
├── images/                   # Lưu trữ hình ảnh hội viên
│   └── members/              # (1.jpg, 3.jpg, ...)
├── qr_codes/                 # Lưu trữ mã QR định danh hội viên đã tạo
│   └── (member_1.png, ...)
├── services/                 # Các dịch vụ xử lý nền
│   └── qr_service.py         # Quản lý luồng camera và nhận diện mã QR
├── styles/                   # Chứa file định nghĩa giao diện
│   └── styles.qss            # Stylesheet định dạng giao diện ứng dụng
├── ui/                       # Giao diện người dùng (PySide6)
│   ├── chart_widget.py       # Thành phần biểu đồ thống kê
│   ├── dashboard_page.py     # Trang thống kê tổng quan
│   ├── login_window.py       # Cửa sổ đăng nhập hệ thống
│   ├── main_window.py        # Cửa sổ chính điều hướng ứng dụng
│   ├── member_page.py        # Quản lý danh sách hội viên
│   ├── qr_checkin_page.py    # Trang thực hiện check-in qua camera
│   └── subscription_page.py  # Quản lý đăng ký gói tập
├── utils/                    # Các công cụ hỗ trợ bổ trợ
├── .gitignore                # Cấu hình bỏ qua các file rác khi đẩy lên GitHub
├── database.py               # Kết nối và thao tác với SQLite
├── gym.db                    # File cơ sở dữ liệu SQLite
├── gym_pic.png               # Logo/Hình ảnh thương hiệu ứng dụng
├── main.py                   # Điểm khởi chạy chính (Entry Point)
└── README.md                 # Tài liệu hướng dẫn dự án

---

## 🚀 Cài đặt và Chạy thử

1. **Cài đặt các thư viện cần thiết:**
   ```bash
   pip install PySide6 opencv-python pyzbar matplotlib pandas openpyxl

👤 Thông tin tác giả
Họ tên: Kiều Quốc Thắng

MSSV: 25AI051

Lớp: 25GAI

Đồ án: Lập trình Python cuối kỳ - Đề tài: 9. Gym and Fitness Center Membership Management.(Phần mềm quản lý phòng Gym).
Dự án được cam kết 100% về tính nguyên bản và tuân thủ các yêu cầu kỹ thuật của bài cuối kỳ.