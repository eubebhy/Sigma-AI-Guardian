# So sánh ba model classifier

Ngày đánh giá: 2026-08-12

Mỗi model được đánh giá bằng cùng classifier flow hiện tại trên 953 cases tại
`xlow`, `low`, `mid`, `strict` và `xstrict`, theo thứ tự tuần tự.

## Độ chính xác

| Model | xlow | low | mid | strict | xstrict |
| --- | ---: | ---: | ---: | ---: | ---: |
| `git-3990c652` | 773/953 | 783/953 | 800/953 | 791/953 | 694/953 |
| `current` | 765/953 | 781/953 | 790/953 | 784/953 | 689/953 |
| `rebuilt` | 766/953 | 781/953 | 791/953 | 784/953 | 689/953 |

## False positive trong lớp học

Càng thấp càng tốt. Mẫu số là 456 cases có expected `Unknown`.

| Model | xlow | low | mid | strict | xstrict |
| --- | ---: | ---: | ---: | ---: | ---: |
| `git-3990c652` | 5 | 6 | 11 | 23 | 124 |
| `current` | 5 | 6 | 12 | 23 | 123 |
| `rebuilt` | 5 | 6 | 11 | 23 | 123 |

## Artifacts

- `summary.json`: metrics, confusion matrix, hash và so sánh chi tiết.
- `outputs/`: output từng case của mọi model và moderation level.
- `training-data-counts.txt`: số lượng training data sau khi rebuild.
