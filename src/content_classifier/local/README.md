# `content_classifier.local`

Nhom module nay phu trach classifier chay model scikit-learn cuc bo qua
`joblib`.

## Thanh phan

- `ai_assistant.py`: wrapper lazy-load model va du doan.
- `classifier.py`: lop/ham boc muc cao hon de goi local AI classifier.

## Du lieu lien quan

- Model runtime hien duoc luu trong `data/models/` va duoc load tu file
  `Ritchie.pkl`.
- Du lieu huan luyen dung cho model nam trong `data/training/`.

## Ghi chu

- Giu module gon, tranh tao them file neu chua that su can.
- Neu `scikit-learn` thieu type stub, chi ignore dung dong bao loi lien quan den
  thu vien nay.
