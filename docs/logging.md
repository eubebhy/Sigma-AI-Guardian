# Qui uoc lam he thong logging

Can hieu kien truc he thong de hieu duoc qui uoc nay. Log level khong bi gioi
han theo file hay layer. `main.py`, feature va adapter deu co the log `DEBUG`,
`INFO`, `WARNING`, `ERROR`, `CRITICAL` khi y nghia cua su kien phu hop.

```text
Adapter
  │
  +─ Khac phuc duoc: info
  │
  +─ Khong khac phuc duoc: raise
  │
  ▼
Feature
  │
  +─ Khac phuc duoc: warning
  │
  +─ Khong khac phuc duoc: raise
  │
  ▼
Main
  │
  +─ Khac phuc duoc: error
  │
  +─ Khong khac phuc duoc: critical log va ket thuc command/process
```

## Log level

```text
DEBUG
    Chi tiet phuc vu debug, nhu input, output, nhanh xu ly va retry.

INFO
    Su kien binh thuong can theo doi, nhu start, shutdown, command hoan tat.

WARNING
    Bat thuong nhung co fallback, retry, skip hoac flow van tiep tuc.

ERROR
    Operation that bai tai layer da quyet dinh xu ly loi do.

CRITICAL
    Main khong the tiep tuc process hoac hoan thanh nhiem vu chinh.
```

## Qui tac

```text
1. Log tai layer quyet dinh recovery.
2. Layer khong xu ly duoc loi phai raise len layer tren.
3. Khong log cung mot loi o nhieu layer, khong vua log vua raise.
4. Main duoc log INFO cho lifecycle va ket qua command binh thuong.
5. ERROR khong bat buoc phai ket thuc process; CRITICAL moi la khong the tiep tuc.
```
