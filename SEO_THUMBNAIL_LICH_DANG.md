# SEO, thumbnail và lên lịch video có sẵn trong Studio

Mở tác vụ **SEO, thumbnail & lên lịch** trong menu của Tuất Videos (`/videos/publishing`).

1. Chọn một hoặc nhiều kênh đã đăng nhập trong **Tài khoản & kênh**, hoặc dán link kênh `/channel/UC…` hay `/@tenkenh`. Nếu nhập link, tool dùng danh sách link thay cho các thẻ kênh phía trên. Ô Video ID cho phép giới hạn vào các video cụ thể đã có trong những kênh này.
2. Chọn trạng thái bản quyền: **Không có vấn đề**, **Có thể bị hạn chế thu nhập / có khiếu nại**, **Bị chặn một phần**, **Bị chặn**. Mặc định chỉ chọn không có vấn đề. Chọn quét hết hoặc giới hạn số video phù hợp mỗi kênh, chọn thứ tự cũ/mới trước, rồi bấm **Quét video**.
3. Bấm **Tìm video tham chiếu** để xem trước. Tool lấy tên bài nhạc ở mốc thời gian đầu tiên trong description; nếu không có tracklist, dùng title hiện tại. Tool tìm YouTube, lấy video thông thường đầu tiên ngoài các video trong danh sách xử lý, giữ nguyên title, description và thumbnail nguồn. Nút hình con mắt ở từng dòng mở nội dung tham chiếu và cho sửa tên bài nhạc nếu cần tìm lại.
4. Dán cookie từ tài khoản `chatgpt.com`, dạng JSON export hoặc chuỗi `name=value; name=value`, rồi bấm **Nạp cookie**. Cookie chỉ giữ trong bộ nhớ của tool; phải nạp lại sau khi đóng/mở tool. Prompt nhập ở đây chỉ dùng để vẽ lại thumbnail. **Title và description được chép nguyên văn từ video tham chiếu, không gửi qua AI để viết SEO.**
5. Chọn ngày bắt đầu, giờ đăng theo Việt Nam (UTC+7) và **Xem lịch dự kiến**. Mỗi kênh có lịch riêng, một video mỗi ngày vào cùng giờ; ngày đã có video được lên lịch sẽ được bỏ qua. Có thể bỏ chọn từng dòng trong bảng.
6. Bấm **Tự động xử lý & lên lịch**. Tool lần lượt tìm tham chiếu còn thiếu, gửi thumbnail tham chiếu và prompt chung tới ChatGPT, lưu ảnh đã vẽ thành JPEG 1280×720 nhỏ hơn 2 MB, chép metadata, tải thumbnail lên Studio và đặt lịch công khai. Video chỉ được đánh dấu hoàn thành sau khi đọc lại đúng metadata và thời gian trên YouTube.

Tool giữ nguyên lịch đã có và không lên lịch lại video đã công khai. Video đang kiểm tra bản quyền hoặc chưa xác định được trạng thái được hiển thị cùng lý do bỏ qua. Hoàn thành kiểm tra bản quyền đơn thuần không được coi là xác nhận video không có khiếu nại.

Tiến độ, nguồn tham chiếu, hội thoại tạo ảnh, đường dẫn thumbnail và từng bước đã xong được lưu qua SQLite. Bấm **Dừng** rồi chạy tiếp các dòng đã chọn để tiếp tục. Khi một yêu cầu đã được gửi nhưng mất phản hồi, tool đọc kết quả trước khi gửi lại. Nếu đã lưu hội thoại ChatGPT, tool quay lại lấy ảnh trong hội thoại đó. Đổi prompt sẽ xóa kết quả ảnh chưa tải lên để có thể tạo lại.

Ảnh mặc định nằm trong thư mục dữ liệu riêng của tool, dưới `publishing_thumbnails/<Channel ID>/<Video ID>.jpg`; có thể chọn thư mục khác. Nút **Xuất CSV** lưu metadata nguồn, lịch, đường dẫn ảnh và kết quả từng dòng.

Tích hợp ChatGPT và tải thumbnail dùng Chrome/Selenium hiện có của tool. Tài khoản cần có quyền tạo ảnh trên ChatGPT và tải thumbnail tùy chỉnh trên YouTube. Nếu Chrome hiện yêu cầu đăng nhập, đồng ý cookie hoặc xác minh, hoàn tất trong cửa sổ Chrome tool mở. Khi hết lượt tạo ảnh, tool giữ tiến độ để chạy tiếp sau. Đọc lại phản hồi từ Studio là bắt buộc; thay đổi giao diện/endpoint có thể khiến dòng báo lỗi thay vì báo thành công.

Tham khảo kỹ thuật: [cookie trong Selenium](https://www.selenium.dev/documentation/webdriver/interactions/cookies/), [tạo/sửa ảnh trong ChatGPT](https://help.openai.com/en/articles/11084440-images-in-chatgpt), [định dạng lệnh Studio dùng trong dự án](https://github.com/yusufusta/ytstudio/blob/master/ytstudio/templates.py).

Kiểm tra tự động dùng dữ liệu và phiên giả lập, không đăng video hay gửi prompt bằng tài khoản thật. Cần kiểm tra tích hợp với phiên đăng nhập thật trước khi dùng cho cả kênh.
