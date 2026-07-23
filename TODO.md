# TODO
- Them he thong config.
- Lam he thong log
- Kiem tra lai tester cua classifier.
- Suy nghi ve he thong da nen tang.
- Web blocker: them canh bao khi unblock site khong ton tai.
- Nang cap classifier.

## TODO trong code hien tai
- `src/system_monitor/keylogger/__init__.py:19`: sau khi hoan thanh config system, dua cac gioi han keylogger vao config (`TODO: After finish config system, add this`).
- `tests/content_classifier/test_all_classifiers.py:314`: rule-based engine co thong bao TODO khi backend khong kha dung.
- `tests/content_classifier/test_all_classifiers.py:330`: local AI backend co thong bao TODO khi backend khong kha dung.
- `tests/content_classifier/test_all_classifiers.py:343`: cloud AI backend chua duoc noi vao test harness.

# Nhung case mat classifier lam sai can fix
(.pyvenv) eubebhy@SigmaDebian:/media/eubebhy/sigma/projects/Sigma-AI-Guardian$ python3 tests/content_classifier/test_all_classifiers.py -fn 100 --strict-level mid
=== main-classifier | strict=mid ===
[FAIL][game] Steam - Black Myth: Wukong | got=Pornography
[FAIL][game] EA SPORTS FC 25 | got=Pornography
[FAIL][game] Path of Exile | got=Gore
[FAIL][game] osu! | got=Pornography
[FAIL][porn] Reddit - r/Rule34: Hot posts this week - Google Chrome | got=Unknown
[FAIL][porn] Naughty America | got=Gore
[FAIL][porn] Digital Playground | got=Unknown
[FAIL][porn] pr0n | got=Unknown
[FAIL][gore] "crime scene photos uncensored" | got=Pornography
[FAIL][gore] "raw battlefield casualties" | got=Game
[FAIL][gore] Crime Scene Photos (Graphic) | got=Unknown
[FAIL][gore] Discord - | got=Unknown
[FAIL][gore] LiveLeak Archive - Graphic Content | got=Unknown
[FAIL][gore] Medical Trauma Archive | got=Unknown
[FAIL][gore] Microsoft Edge - LiveLeak archive mirror | got=Unknown
[FAIL][gore] Raw Battlefield Casualties | got=Game
[FAIL][gore] Surgical Operation (Uncensored) | got=Pornography
[FAIL][gore] bestg0re | got=Pornography
[FAIL][unknown] chrome - anh anime | got=Pornography
[FAIL][unknown] Pascal - BAI1.PAS | got=Pornography
[FAIL][unknown] st | got=Pornography
[FAIL][unknown] WSL | got=Pornography
[FAIL][unknown] Gcc | got=Pornography
[FAIL][unknown] tcc | got=Pornography
[FAIL][unknown] a | got=Pornography
[FAIL][unknown] e | got=Pornography
[FAIL][unknown] c | got=Pornography
[FAIL][unknown] d | got=Pornography
[FAIL][unknown] g | got=Pornography


