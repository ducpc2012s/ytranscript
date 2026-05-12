# Transcript Studio

Web app nhỏ dùng source local từ
[`jdepoix/youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api)
để lấy transcript YouTube theo 2 dạng: có timestamp hoặc không có timestamp.

## Chạy local

```powershell
python -m pip install -r requirements.txt
python app.py
```

Sau đó mở:

```text
http://127.0.0.1:8000
```

## Cách dùng

1. Dán link YouTube hoặc video ID.
2. Chọn `Không timestamp` hoặc `Có timestamp`.
3. Nhập ngôn ngữ ưu tiên dạng `vi,en` nếu muốn đổi thứ tự tìm caption.
4. Copy kết quả hoặc tải file `.txt`.

## Ghi chú

- App import thư viện trực tiếp từ thư mục `upstream`, là clone của repo gốc.
- Nếu đã có thư mục `.vendor`, app sẽ ưu tiên dùng dependency local trong đó.
- YouTube phải có captions/subtitles cho video thì thư viện mới lấy được transcript.
- Một số IP/cloud network có thể bị YouTube chặn; lỗi này sẽ được hiển thị trực tiếp trên giao diện.
