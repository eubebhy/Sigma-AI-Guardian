# Hiệu năng và benchmark

## TL;DR

Chưa có benchmark gate đáng tin cậy. Classifier rule/fuzzy là hotspot từ source;
screen-capture benchmark chỉ chạy manual trên desktop thật. Không tối ưu trước khi có
corpus và metric cố định.

## Quan sát không dùng làm baseline

- Rule/fuzzy classifier không giới hạn số ký tự hoặc token trước khi so khớp; đây là
  rủi ro hiệu năng từ source, chưa có benchmark tái lập được commit trong repository.
- Log lịch sử classifier có sample size/setting khác nhau; không phải baseline so
  sánh trực tiếp.
- `tests/test_screen_capture.py real benchmark ...` đọc màn hình thật, chịu ảnh hưởng
  resolution, compositor, desktop load và sharpness.

## Benchmark cần có khi sửa khu vực tương ứng

| Khu vực | Metric | Corpus/môi trường | Regression trigger |
| --- | --- | --- | --- |
| `clean_text` + rule classifier | p50/p95 latency, chars/s, result | Fixed normal + adversarial text fixture | Vượt budget đã duyệt hoặc đổi expected label. |
| Main classifier | cold/warm latency, RSS, label quality | Fixed model hash, fixed corpus, isolated process | Regression rõ so baseline cùng machine. |
| Screen capture | FPS, frame time, memory | Resolution/monitor/sharpness ghi rõ | Chỉ điều tra khi same environment giảm vượt ngưỡng. |
| Input listener | queue depth, dropped/coalesced event | Fake producer/consumer | Unbounded growth hoặc sai down/up ordering. |

## Quy tắc benchmark

- Tách benchmark khỏi unit test/CI correctness.
- Ghi Python, OS, CPU, screen resolution, dependency/model hash, sample size và warmup.
- Dùng median/p95, không kết luận từ một lần chạy.
- Không benchmark bằng dữ liệu clipboard/window title thật hoặc commit log runtime lớn.
