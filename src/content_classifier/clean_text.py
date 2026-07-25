"""Chuẩn hoá văn bản bị che giấu trước khi phân loại nội dung.

File path: `src/content_classifier/clean_text.py`
Input: chuỗi text gốc lấy từ web, clipboard hoặc nguồn giám sát khác.
Output: chuỗi text đã chuẩn hoá để rule-based và local classifier dễ so khớp.

Luồng xử lý của `clean_text()`:
1. Chuẩn hoá Unicode theo NFKC, xoá ký tự zero-width và thay ký tự giả mạo từ
   bảng chữ cái Greek/Cyrillic bằng ký tự Latin tương ứng.
2. Ghép từ bị tách bằng `._/\\-`, ví dụ `h-e-n-t-a-i` thành `hentai`.
3. Ghép chuỗi ký tự đơn bị cách bằng khoảng trắng nếu kết quả thuộc danh sách
   cần nhận diện, ví dụ `h e n t a i` thành `hentai`.
4. Đổi dấu phân cách nằm giữa hai từ thành phép nối hoặc khoảng trắng. Dấu được
   bỏ khi một phía chỉ có một ký tự; hai từ đầy đủ được ngăn bằng khoảng trắng.
5. Chuẩn hoá leet-speak khi ký tự thay thế nằm xen giữa chữ cái, rồi fuzzy-match
   token chưa được sửa leet với các từ thuộc kho phrase. Token chỉ bị fuzzy-match
   khi độ tương đồng lớn hơn 80%.
6. Thu gọn khoảng trắng trước khi trả kết quả cho classifier.

Ví dụ:
- `h-e-n-t-a-i w4r` -> `hentai war`
- `h e n t a i` -> `hentai`
- `safe_document` -> `safe document`
- `rule 34` -> `rule 34`

Giới hạn quan trọng:
- Fuzzy matching chỉ dùng từ lấy từ các phrase khai báo trong module, không tự
  đoán từ ngoài danh sách.
- Cache fuzzy có tối đa 4096 token để tránh tính lại `SequenceMatcher` cho các
  tiêu đề lặp lại.
- Module chỉ chuẩn hoá text; quyết định category thuộc về classifier phía sau.
"""

from difflib import SequenceMatcher
from functools import lru_cache
import re
import unicodedata


# Các ký tự vô hình thường được chèn vào giữa từ để né bộ lọc.
ZERO_WIDTH_CHARS = {
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\ufeff": "",
    "\u2060": "",
}


# Ký tự có hình dáng gần giống Latin nhưng có mã Unicode khác.
CONFUSABLE_CHARS = {
    # Greek / Cyrillic common spoof chars
    "ο": "o",  # Greek omicron
    "Ο": "O",
    "о": "o",  # Cyrillic o
    "О": "O",
    "а": "a",
    "А": "A",
    "е": "e",
    "Е": "E",
    "і": "i",
    "І": "I",
    "Ι": "I",
    "ⅼ": "l",
    "Ι": "I",
    "р": "p",
    "Р": "P",
    "с": "c",
    "С": "C",
    "х": "x",
    "Х": "X",
}


# Các phép thay thế leet-speak phổ biến trong tên trang và tiêu đề.
LEET_CHARS = {
    "0": "o",
    "3": "e",
    "4": "a",
    "@": "a",
    "1": "i",
    "!": "i",
    "|": "i",
}


# Chỉ những dấu này được xem là dấu dùng để cố tình tách một từ.
SEP_CHARS = r"._/\\-"


# Các phrase cung cấp từ chuẩn cho bước fuzzy matching. Chúng không trực tiếp
# quyết định category; category vẫn do rule-based hoặc local AI xử lý.
GAME_PHRASES = {
    "black myth wukong",
    "path of exile",
    "steam",
    "epic games",
    "riot games",
    "valorant",
    "league of legends",
    "minecraft",
    "roblox",
    "genshin impact",
    "counter strike",
    "csgo",
    "cs2",
    "dota",
    "fortnite",
}


ADULT_PHRASES = {
    "spankbang",
    "onlyfans",
    "fansly",
    "camsoda",
    "chaturbate",
    "stripchat",
    "livejasmin",
    "myfreecams",
    "brazzers",
    "reality kings",
    "naughty america",
    "bangbros",
    "vixen",
    "digital playground",
    "fake taxi",
    "adult video",
    "hentai",
    "doujin",
    "bukkake",
    "rule34",
    "rule 34",
    "nhentai",
    "hentai haven",
    "jav",
    "uncensored jav",
}


GORE_PHRASES = {
    "crime scene photos",
    "crime scene photos uncensored",
    "fatal accident cctv",
    "raw battlefield casualties",
    "battlefield casualties",
    "animal attack graphic",
    "graphic accident",
    "graphic accident compilation",
    "graphic violence",
    "graphic violence compilation",
    "liveleak archive",
    "liveleak archive mirror",
    "medical trauma archive",
    "nsfl",
    "nsfl crash footage",
    "nsfl thread",
    "nsfl discussion",
    "crash footage",
    "fatal workplace accident",
    "surgical operation uncensored",
    "train accident graphic",
    "war combat footage graphic",
    "war combat footage",
    "beheading",
    "beheading video",
    "blood gore",
    "best gore",
    "cartel execution",
    "graphic violence compilation",
}


# Danh sách giới hạn cho trường hợp từng ký tự bị tách bằng khoảng trắng. Việc
# giới hạn này tránh ghép nhầm câu tự nhiên như `a b c` thành một từ mới.
OBFUSCATED_WORDS = {
    "hentai",
    "doujin",
    "bukkake",
    "adult",
    "video",
    "spankbang",
    "onlyfans",
    "fansly",
    "camsoda",
    "chaturbate",
    "stripchat",
    "livejasmin",
    "myfreecams",
    "brazzers",
    "bangbros",
    "vixen",
    "nsfl",
    "gore",
    "blood",
    "graphic",
    "violence",
    "compilation",
    "beheading",
    "execution",
    "cartel",
    "combat",
    "footage",
    "battlefield",
    "casualties",
    "accident",
    "fatal",
    "crime",
    "scene",
    "photos",
}


def _translate_chars(text: str, table: dict[str, str]) -> str:
    """Thay từng ký tự theo bảng và giữ nguyên ký tự không có trong bảng."""
    return "".join(table.get(ch, ch) for ch in text)


def _normalize_unicode(text: str) -> str:
    """Đưa Unicode về dạng thống nhất rồi loại ký tự vô hình/giả mạo."""
    text = unicodedata.normalize("NFKC", text)
    text = _translate_chars(text, ZERO_WIDTH_CHARS)
    text = _translate_chars(text, CONFUSABLE_CHARS)
    return text


def _leet_normalize_token(token: str) -> str:
    """Đổi leet-speak khi có ký tự thay thế nằm xen giữa hai chữ cái.

    Khi tìm thấy mẫu như `g0r` hoặc `g4m`, toàn bộ ký tự leet trong token được
    thay để `g0r3` thành `gore` và `g4m3` thành `game`. Token số như `34` hoặc
    hậu tố số như `rule34` được giữ nguyên.
    """
    has_interleaved_leet = False
    for index, char in enumerate(token):
        if char not in LEET_CHARS or index == 0 or index == len(token) - 1:
            continue
        if token[index - 1].isalpha() and token[index + 1].isalpha():
            has_interleaved_leet = True
            break

    if not has_interleaved_leet:
        return token
    return "".join(LEET_CHARS.get(ch, ch) for ch in token)


# Chuẩn bị dữ liệu một lần khi import: tách mọi phrase thành từ đơn, chuẩn hoá,
# loại trùng và sắp xếp để fuzzy matching có thứ tự ổn định.
_PHRASE_WORDS = tuple(
    sorted(
        {
            _leet_normalize_token(word).lower()
            for phrase in GAME_PHRASES | ADULT_PHRASES | GORE_PHRASES
            for word in re.findall(r"[^\W_]+", phrase, flags=re.UNICODE)
        }
    )
)
_PHRASE_WORD_SET = frozenset(_PHRASE_WORDS)
# Nhóm từ theo độ dài để mỗi token chỉ so với các ứng viên có kích thước gần nó.
_PHRASE_WORDS_BY_LENGTH = {
    length: tuple(word for word in _PHRASE_WORDS if len(word) == length)
    for length in {len(word) for word in _PHRASE_WORDS}
}
_FUZZY_MATCH_THRESHOLD = 0.80


@lru_cache(maxsize=4096)
def _closest_phrase_word(token: str) -> str:
    """Trả từ phrase giống token nhất khi điểm vượt ngưỡng 80%.

    Từ đã khớp chính xác được trả ngay. Với từ chưa khớp, hàm chỉ xét ứng viên
    dài khoảng 2/3 đến 3/2 độ dài token để giảm số phép `SequenceMatcher`.
    Nếu không ứng viên nào vượt ngưỡng, token gốc được giữ nguyên. Kết quả được
    `lru_cache` giữ lại vì tiêu đề cửa sổ và URL thường xuất hiện nhiều lần.
    """

    if token in _PHRASE_WORD_SET:
        return token

    closest_word = token
    closest_score = _FUZZY_MATCH_THRESHOLD
    minimum_length = max(1, len(token) * 2 // 3)
    maximum_length = len(token) * 3 // 2 + 1
    for length in range(minimum_length, maximum_length + 1):
        for phrase_word in _PHRASE_WORDS_BY_LENGTH.get(length, ()):
            score = SequenceMatcher(None, token, phrase_word).ratio()
            if score > closest_score:
                closest_word = phrase_word
                closest_score = score
    return closest_word


def _join_separator_split_words(text: str) -> str:
    """Ghép token bị chèn dấu như `h-e-n-t-a-i` thành `hentai`.

    `[^\\W_]` theo ý nghĩa regex Unicode được dùng để nhận chữ hoặc số nhưng
    không nhận dấu gạch dưới. Hai lookaround bảo đảm pattern không lấy một phần
    nằm giữa token lớn hơn.
    """

    pattern = (
        rf"(?<![^\W_])"
        rf"(?:[^\W_][{re.escape(SEP_CHARS)}])+[^\W_]"
        rf"(?![^\W_])"
    )

    def repl(match: re.Match[str]) -> str:
        raw = match.group(0)
        return re.sub(rf"[{re.escape(SEP_CHARS)}]", "", raw)

    return re.sub(pattern, repl, text, flags=re.UNICODE)


def _join_space_split_words(text: str) -> str:
    """Ghép từ bị tách từng ký tự nếu kết quả nằm trong danh sách cần bắt.

    Ví dụ `h e n t a i` được thử thành `hentai`. Chuỗi không thuộc
    `OBFUSCATED_WORDS` được trả nguyên trạng để tránh ghép nhầm văn bản hợp lệ.
    """

    pattern = r"(?<![^\W_])(?:[^\W_]\s+){2,}[^\W_](?![^\W_])"

    def repl(match: re.Match[str]) -> str:
        raw = match.group(0)
        joined = re.sub(r"\s+", "", raw)
        canonical = _leet_normalize_token(joined).lower()

        if canonical in OBFUSCATED_WORDS:
            return canonical

        return raw

    return re.sub(pattern, repl, text, flags=re.UNICODE)


def _replace_separator_between_words(text: str) -> str:
    """Chuẩn hoá dấu phân cách nằm giữa hai phần của token.

    Nếu một phía chỉ có một ký tự, hai phía được nối liền để tiếp tục phục hồi
    kiểu che giấu `h-ent-ai`. Nếu cả hai phía là từ đầy đủ, dấu được đổi thành
    khoảng trắng, ví dụ `safe_document` thành `safe document`.
    """

    pattern = (
        r"([^\W_]+)"
        r"(_ |- |\. |/ |\\ |-|_|\.|/|\\)"
        r"([^\W_]+)"
    )

    def repl(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(3)

        if len(left) == 1 or len(right) == 1:
            return left + right

        return left + " " + right

    current_text = text

    # Một chuỗi có thể chứa nhiều dấu liên tiếp. Lặp đến khi không còn match để
    # đầu ra của lần thay trước tiếp tục được xử lý ở lần sau.
    while True:
        current_text, count = re.subn(
            pattern,
            repl,
            current_text,
            flags=re.UNICODE,
        )
        if count == 0:
            break

    return current_text


def _normalize_obfuscated_tokens(text: str) -> str:
    """Chuẩn hoá leet rồi fuzzy-match từng token với kho phrase.

    Pattern vẫn giữ `@!|` bên trong token để các dạng như `hent@i` được xử lý
    như một đơn vị thay vì bị tách thành nhiều từ độc lập. Token vừa được sửa
    leet được trả ngay để từ đúng như `game` không bị fuzzy đổi thành `games`.
    """

    def repl(match: re.Match[str]) -> str:
        raw_token = match.group(0)
        leet_token = _leet_normalize_token(raw_token)
        canonical = leet_token.lower()
        if leet_token != raw_token:
            return canonical
        return _closest_phrase_word(canonical)

    token_pattern = r"[^\W_]+(?:[@!|][^\W_]+)*"
    return re.sub(token_pattern, repl, text, flags=re.UNICODE)


def _collapse_spaces(text: str) -> str:
    """Đổi mọi cụm whitespace thành một khoảng trắng và bỏ khoảng trắng biên."""
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """Chạy toàn bộ pipeline giảm obfuscation và trả text đã chuẩn hoá.

    Các bước được giữ theo thứ tự vì đầu ra của bước trước là đầu vào cần thiết
    cho bước sau: Unicode phải được thống nhất trước khi nhận diện separator;
    token phải được ghép lại trước khi sửa leet và fuzzy-match; khoảng trắng
    chỉ được thu gọn sau khi mọi phép nối/tách đã hoàn tất.

    Hàm không đọc file, không gọi model và không quyết định category.
    """

    # 1. Chuẩn hoá các ký tự có nhiều biểu diễn hoặc dùng để giả mạo.
    text = _normalize_unicode(text)
    # 2-4. Khôi phục token bị chia nhỏ bằng dấu hoặc khoảng trắng.
    text = _join_separator_split_words(text)
    text = _join_space_split_words(text)
    text = _replace_separator_between_words(text)
    # 5. Sửa leet và lỗi gần đúng dựa trên kho phrase giới hạn.
    text = _normalize_obfuscated_tokens(text)
    # 6. Dọn khoảng trắng được tạo ra trong các bước phía trên.
    text = _collapse_spaces(text)
    return text
