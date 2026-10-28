# Ghép nhạc và đổi tiêu đề video

Trong mục **Tác vụ** ở thanh bên, mở **Ghép & đổi tiêu đề**.

1. Chọn một kênh đã đăng nhập trong Tuất.
2. Chọn **Theo số lượng** để lấy số video mới nhất sau khi lọc, hoặc **Theo khoảng ngày** để quét toàn bộ video từ ngày bắt đầu đến hết ngày kết thúc (giờ Việt Nam). Phạm vi gồm tất cả video, chỉ công khai, đã lên lịch hoặc bản nháp. Loại ngày có thể là ngày tải lên, ngày công khai, ngày lên lịch hoặc tự động theo trạng thái video.
3. Bấm **Quét video**. Tác vụ đọc cả video tải lên và bản lưu livestream, không phụ thuộc audio có lỗi hay đang xử lý. Video chưa có thời lượng sẽ được giữ trong bảng nhưng chưa tự ghép.
4. Chọn thư mục nhạc, bật quét thư mục con nếu cần, đặt **Lệch tối đa (giây)** rồi bấm **Ghép theo thời lượng**. Mặc định lệch tối đa 2 giây. Các định dạng nhạc dùng cùng danh sách hỗ trợ với chức năng audio hiện có.
5. Xem bảng: Video ID, tiêu đề lúc quét, thời lượng video/nhạc, file ghép, độ lệch và tiêu đề mới. Tiêu đề mới lấy từ tên file nhạc bỏ đuôi mở rộng, lọc ký tự không hợp lệ và rút gọn trong giới hạn 100 đơn vị UTF-16, giữ nguyên emoji hoàn chỉnh.
6. Khi nhiều bài khớp, ưu tiên bài gần thời lượng nhất. Nếu nhiều tên khớp ngang nhau và tiêu đề cũ không xác định được một bài duy nhất, dòng báo **Cần chọn file**. Bấm biểu tượng thư mục ở cuối dòng để chọn một trong các bài khớp. Các dòng khớp được chọn sẵn; bỏ chọn dòng chưa muốn đổi.
7. Bấm **Đổi tiêu đề đã chọn** để cập nhật trực tiếp tiêu đề trên YouTube bằng phiên kênh Tuất. Chỉ những dòng đã chọn và có tiêu đề đề xuất mới được xử lý.

Tool đọc lại đúng Video ID, kênh, thời lượng và tiêu đề trước khi gửi. Nếu tiêu đề đã bị sửa thủ công sau lúc quét hoặc thời lượng không còn khớp, dòng báo lỗi để quét lại. Yêu cầu cập nhật chỉ chứa thay đổi tiêu đề. **Thành công** chỉ hiện sau khi đọc lại thấy đúng tiêu đề mới trên YouTube.

Một file nhạc có thể ghép cho nhiều video. Thao tác này đổi tiêu đề trên YouTube, giữ nguyên các file video/nhạc trên máy. **Xuất kết quả CSV** lưu tiêu đề cũ, tiêu đề mới và trạng thái để đối chiếu.

**Dừng** ngừng các bước tiếp theo sau yêu cầu đang thực hiện. Tải lại trang hoặc chuyển trang vẫn giữ tiến độ; khi mở lại ứng dụng, dòng đang xử lý được đưa về trạng thái có thể chạy tiếp. Mỗi lượt chạy lại đọc YouTube trước, nên tiêu đề đã đúng sẽ được xác nhận thay vì gửi lại. Cập nhật HTTP bị mất phản hồi cũng phải được đọc lại trước khi báo thành công.

Kiểm tra lập trình: `python -X utf8 -m unittest tests.test_video_titles -v`. Các kiểm tra dùng kênh giả, request giả và audio mẫu cục bộ, không đổi tiêu đề video thật.
