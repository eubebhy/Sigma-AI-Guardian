# `content_classifier`

Package nay chua cac module phan loai noi dung cua du an.

## Thong tin module

- `file path`: `src/content_classifier/`
- `input`: chuoi van ban dau vao can phan loai.
- `output`: nhan `ContentCategory` tuong ung voi noi dung dau vao.
- `nguyen ly hoat dong`: cac classifier trong package nay chuan hoa text, so khop theo quy tac hoac suy luan tu model cuc bo, roi tra ve danh muc phu hop.

## Thanh phan

- `tags.py`: dinh nghia `ContentCategory`.
- `clean_text.py`: chuan hoa text truoc khi so khop tu khoa.
- `rule_based/`: classifier dua tren tu khoa.
- `local/`: classifier chay model scikit-learn cuc bo qua `joblib`.
- `cloud/`: cho danh cho classifier chay qua dich vu cloud, hien chua trien khai.

## Quy uoc

- Moi module chi nen lam mot viec ro rang.
- Ham noi bo nen bat dau bang `_`.
- Giu ten file va ten package khop voi layout hien tai trong `src/content_classifier/`.

```python
def classify(text: str, strict_level: str) -> ContentCategory:
    """Phan loai van ban dau vao va tra ve ContentCategory tuong ung."""
    pass
```

Sau do trong ./__init__.py se tong hop cac api phan loai lai va tao thanh 1 api duy nhat.

