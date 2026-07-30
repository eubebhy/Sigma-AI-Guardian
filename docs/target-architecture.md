# Kiến trúc đích: SAG Server, SAG Service và SAG Agent

## Phạm vi

SAG gồm một Server trung tâm và nhiều máy học sinh. Mỗi máy học sinh có hai thành
phần: SAG Service và SAG Agent. Tài liệu này chỉ mô tả trách nhiệm kiến trúc; cơ chế
giao tiếp, format dữ liệu và tool call chưa được thiết kế.

## Sơ đồ tổng thể

```text
Teacher Console
      |
      v
SAG Server
      |
      v
SAG Service x N
      |
      v
SAG Agent x N
      |
      v
Windows/Linux desktop
```

SAG Server là điểm trung tâm giữa Teacher Console và các máy học sinh. Teacher Console
không giao tiếp trực tiếp với SAG Service, SAG Agent hoặc desktop của máy học sinh.

## Trách nhiệm

| Thành phần | Chịu trách nhiệm | Không chịu trách nhiệm |
| --- | --- | --- |
| Teacher Console | Giáo viên tạo yêu cầu và xem trạng thái/kết quả | Gọi API hệ điều hành hoặc desktop máy học sinh |
| SAG Server | Nhận yêu cầu giáo viên, điều phối đến máy học sinh và quản lý trạng thái phía Server | Thao tác desktop hoặc API Windows/Linux |
| SAG Service | Khởi động cùng hệ điều hành, kết nối và giao tiếp với SAG Server, chuyển việc đến SAG Agent | Trực tiếp gọi tool, feature hoặc API desktop |
| SAG Agent | Gọi tool/feature cục bộ, quản lý lifecycle của tool và shutdown sạch | Kết nối Server hoặc quản lý session phía Server |
| Platform adapter | Thực thi khác biệt Windows/Linux cho SAG Agent | Network, session hoặc nghiệp vụ Server |

## SAG Service

SAG Service là tiến trình nền trên máy học sinh. Nó khởi động cùng hệ điều hành bằng
Windows Service trên Windows hoặc service manager như `systemd` hay OpenRC trên Linux.

Service chịu trách nhiệm duy trì kết nối và giao tiếp với SAG Server. Khi cần mở rộng,
Service cũng là nơi quản lý session gắn với account hoặc học sinh. Service không trực
tiếp thao tác desktop; nó yêu cầu SAG Agent thực hiện công việc cục bộ.

## SAG Agent

SAG Agent là chương trình thực thi cục bộ. Agent nhận công việc từ SAG Service, gọi các
tool và feature đã có, quản lý lifecycle tài nguyên của chúng, rồi shutdown sạch khi
được yêu cầu. Agent là boundary duy nhất được phép thao tác Windows/Linux desktop.

## Trạng thái hiện tại

Repository hiện chỉ có Agent cục bộ với `status` và platform runtime. SAG Server, SAG
Service, cơ chế Service–Agent và Teacher Console chưa tồn tại. Xem
[`architecture.md`](architecture.md) để biết code đang có.
