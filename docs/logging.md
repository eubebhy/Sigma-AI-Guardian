# Qui uoc lam he thong logging.
Nen hieu so qua kien truc he thong de hieu duoc so do nay
```text
Adapter
  │
  +─ Co the khac phuc
  │      INFO/WARNING
  │
  +─ raise
  │
  ▼
Feature
  │
  +─ Co the khac phuc
  │      WARNING/ERROR
  │
  +─ raise
  │
  ▼
Main
  │
  +─ Co the khac phuc
  │      ERROR
  │
  +─ Cannot recover
          CRITICAL
```

