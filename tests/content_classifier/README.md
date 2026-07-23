# `tests/content_classifier`

Thu muc nay chua bo test cho cac classifier cua `content_classifier`.

## Ghi chu

- File runner: `tests/content_classifier/test_all_classifiers.py`
- Dau vao:
  - CLI flag de chon engine, theme, cach lay sample.
  - Cac file case trong `tests/content_classifier/test_cases/`
- Dau ra:
  - In tung dong `PASS` / `FAIL` cho case phu hop.
  - In `Summary` theo tong so case va theo tung theme.
- Cach hoat dong:
  - Runner tu suy ra root project tu vi tri file hien tai.
  - Runner them `src/` vao `sys.path` roi import package bang absolute import.
  - Moi dong trong file case duoc parse thanh 1 test case va map sang `ContentCategory` mong doi.

## Thanh phan

- `test_all_classifiers.py`: test runner cho rule-based, local AI va cloud AI.
- `test_clean_text.py`: unit test va CLI de thu `clean_text` voi chuoi tuy y.
- `test_cases/`: du lieu test theo tung nhom noi dung.
- `test_cases/clean_text.json`: cac cap `input`/`expected` rieng cho clean text.

## Tep case

- `game.txt`: case can ra `Game`.
- `porn.txt`: case can ra `Pornography`.
- `gore.txt`: case can ra `Gore`.
- `unknown.txt`: case can ra `Unknown`.

## Quy uoc case

- Moi dong la mot case.
- Co the dung `#` de ghi comment ca dong hoac comment cuoi dong.
- Phan parser se bo moi thu sau ky tu `#`.

## Flag cua test runner

- `-r`: chay rule-based classifier.
- `-l`: chay local AI classifier.
- `-c`: chay cloud AI placeholder.
- `-f` / `--show-failures`: hien case loi.
- `-m` / `--mode`: chon `all`, `game`, `porn`, hoac `gore`.
- `-p` / `--pick-mode`: chon `sequential` hoac `random`.
- `-n` / `--sample-size`: so case toi da lay tu moi nhom.
- `--strict-level`: chon `xlow`, `low`, `mid`, `strict`, hoac `xstrict`; mac
  dinh la `mid`.

## Chay thu cong

Nen dung Python trong virtualenv cua project de tranh thieu dependency nhu `rapidfuzz`.

```bash
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py -r
```

Vi du:

```bash
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py -r -f
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py -r --strict-level strict
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py -r -m gore -n 5
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py -l -m all -p random -n 3
```

Neu muon xem huong dan:

```bash
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py --help
```

## Test clean text

Chay toan bo cases rieng cua `clean_text`:

```bash
./.pyvenv/bin/python tests/content_classifier/test_clean_text.py
```

Clean nhanh mot chuoi tu CLI:

```bash
./.pyvenv/bin/python tests/content_classifier/test_clean_text.py --text "hent@i w4r"
```


Dang test copilot, hay goi y cho t text ngau nhien neu m dang hoat dong.
