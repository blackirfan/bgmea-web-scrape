"""Turn one raw BGMEA member Details page into the nine business fields.

The page is server-rendered static HTML with three tab panes (Company, Address,
Final) that are all present in the DOM even when not visible. Extraction is
label-driven: every value is found by the text of its <th> row header, never by
column position, so a layout tweak degrades to a blank plus an audit note
rather than a wrong value.

`extract(page_source, url)` is pure and unit-tested; the Selenium driver only
supplies `driver.page_source`.
"""

import re

try:
    from bs4 import BeautifulSoup
    _HAVE_BS4 = True
except ImportError:  # keep the project dependency-light; fall back to a parser
    from html.parser import HTMLParser
    _HAVE_BS4 = False


# --------------------------------------------------------------------------- #
#  value normalisation                                                        #
# --------------------------------------------------------------------------- #

def _ws(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def clean_int(value):
    """'1,250 workers' -> 1250. Returns None when there is no usable number.

    A bare 0 is treated as 'not reported': BGMEA's form defaults empty numeric
    fields to 0, and we never want a guessed zero in the output.
    """
    if value is None:
        return None
    text = re.sub(r"(?i)\b(workers?|persons?|pcs|nos?|machines?)\b", " ", str(value))
    text = text.replace(",", "")
    m = re.search(r"\d+", text)
    if not m:
        return None
    number = int(m.group(0))
    return number or None


def clean_registration(value):
    """Registration numbers stay strings: '5161' never becomes 5161.0."""
    text = _ws(value)
    if not text or text in {"0", "-", "N/A", "n/a"}:
        return None
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        text = text.split(".")[0]
    return text


_WOVEN = re.compile(r"(?i)\bwoven\b")
_KNIT = re.compile(r"(?i)\bknit(?:wear|ting)?\b")
_COMPOSITE = re.compile(r"(?i)\bcomposite\b")
_SWEATER = re.compile(r"(?i)\bsweater\b")


def normalise_type(values):
    """Map BGMEA type rows to exactly 'woven' / 'knit' / 'both' / None.

    Returns (value, note). 'Composite' or 'Sweater' on their own are left blank
    with a note rather than guessed, as the source methodology does not say
    which base fabric they use.
    """
    parts = [v for v in (values or []) if _ws(v)]
    if not parts:
        return None, "factory type not listed on the page"
    blob = " , ".join(parts)
    woven, knit = bool(_WOVEN.search(blob)), bool(_KNIT.search(blob))
    if woven and knit:
        return "both", None
    if woven:
        return "woven", None
    if knit:
        return "knit", None
    if _COMPOSITE.search(blob) or _SWEATER.search(blob):
        return None, f"factory type not normalised (source: {blob})"
    return None, f"factory type not normalised (source: {blob})"


def normalise_capacity(raw, period_hint):
    """Keep the unit attached: '600000' + 'yearly dozen' -> '600000 dozen/year'."""
    text = _ws(raw)
    if not text or text in {"0", "-"}:
        return None
    if re.search(r"(?i)(pcs|dozen|piece|/|per|month|year)", text):
        return text
    if period_hint:
        measure = "dozen" if "dozen" in period_hint else (
            "pcs" if "pc" in period_hint else "")
        period = "year" if "year" in period_hint else (
            "month" if "month" in period_hint else "")
        unit = "/".join(p for p in (measure, period) if p)
        if unit:
            return f"{text} {unit}"
    return text


# --------------------------------------------------------------------------- #
#  HTML -> rows                                                               #
# --------------------------------------------------------------------------- #

class _RowParser(HTMLParser if not _HAVE_BS4 else object):
    """Minimal stand-in used only when BeautifulSoup is not installed."""

    def __init__(self):
        super().__init__()
        self.rows = []          # list of (th_text, td_text)
        self._stack = []
        self._cur_tag = None
        self._th, self._td = [], []
        self._in_th = self._in_td = False
        self._title = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._th, self._td = [], []
        elif tag == "th":
            self._in_th = True
        elif tag == "td":
            self._in_td = True
        elif tag == "title":
            self._in_title = True
        elif tag == "br" and self._in_td:
            self._td.append("\n")

    def handle_endtag(self, tag):
        if tag == "th":
            self._in_th = False
        elif tag == "td":
            self._in_td = False
        elif tag == "title":
            self._in_title = False
        elif tag == "tr":
            self.rows.append(("".join(self._th), "".join(self._td)))

    def handle_data(self, data):
        if self._in_th:
            self._th.append(data)
        elif self._in_td:
            self._td.append(data)
        elif self._in_title:
            self._title.append(data)

    @property
    def title(self):
        return "".join(self._title)


def _rows_and_title_bs4(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    rows = []
    for tr in soup.select("tr"):
        th = tr.find("th")
        td = tr.find("td", recursive=False) or tr.find("td")
        if th is None:
            continue
        for br in tr.find_all("br"):
            br.replace_with("\n")
        rows.append((_ws(th.get_text(" ")),
                     td.get_text("\n") if td is not None else ""))
    title = soup.title.get_text() if soup.title else ""
    # nested type / employee tables
    return soup, rows, title


def _nested_table_values(soup, header_label):
    """Return the list of body-cell rows for the inner table under a header."""
    for th in soup.select("th[scope=row], th"):
        if header_label.lower() in _ws(th.get_text(" ")).lower():
            tr = th.find_parent("tr")
            inner = tr.find("table") if tr else None
            if inner is None:
                return []
            out = []
            for row in inner.select("tbody tr"):
                cells = [_ws(td.get_text(" ")) for td in row.find_all("td")]
                if any(cells):
                    out.append(cells)
            return out
    return []


# --------------------------------------------------------------------------- #
#  public entry point                                                         #
# --------------------------------------------------------------------------- #

BUSINESS_COLUMNS = [
    "Name of factory",
    "BGMEA registration no.",
    "Address of factory",
    "Factory type (woven, knit, both)",
    "management",
    "Employee_male",
    "Employee_female",
    "No. of machines",
    "Production capacity",
]


def _find_row(rows, *needles):
    for label, value in rows:
        low = label.lower()
        if any(n in low for n in needles):
            return value
    return None


def _address_lines(value):
    out = []
    for line in (value or "").split("\n"):
        line = _ws(line)
        if not line:
            continue
        if re.match(r"(?i)^(phone|email|fax|mobile|tel|website)\b", line):
            continue
        if re.fullmatch(r"[\d\s\-+()/,.]{4,}", line):
            continue
        if "@" in line and " " not in line:
            continue
        out.append(line)
    return out


def extract(page_source, url=None):
    """Return (record_dict, notes_list). Never raises on bad content."""
    notes = []

    if _HAVE_BS4:
        soup, rows, title = _rows_and_title_bs4(page_source)
    else:
        p = _RowParser()
        p.feed(page_source)
        soup, rows, title = None, p.rows, p.title
        rows = [(_ws(a), b) for a, b in rows]

    # -- name -------------------------------------------------------------- #
    name = None
    if title:
        name = _ws(re.sub(r"(?i)^\s*BGMEA\s*\|\s*Member\s*Details\s*", "", title))
    if not name:
        m = re.search(r"<thead[^>]*>.*?<th[^>]*>\s*<strong>(.*?)</strong>",
                      page_source, re.S | re.I)
        if m:
            name = _ws(re.sub(r"<[^>]+>", "", m.group(1)))

    # -- registration ---------------------------------------------------- #
    reg = clean_registration(_find_row(rows, "reg. no", "reg no", "registration no"))

    # -- factory type --------------------------------------------------- #
    type_values = []
    if _HAVE_BS4:
        for cells in _nested_table_values(soup, "Factory Type"):
            if cells and cells[0].lower() not in {"type", "priority"}:
                type_values.append(cells[0])
    else:
        raw = _find_row(rows, "factory type")
        if raw:
            for tok in re.split(r"[\n,]", raw):
                tok = _ws(tok)
                if tok and tok.lower() not in {"type", "priority"}:
                    type_values.append(tok)
    ftype, type_note = normalise_type(type_values)
    if type_note:
        notes.append(type_note)

    # -- employees / management --------------------------------------- #
    management = male = female = None
    emp_rows = _nested_table_values(soup, "No. of Employees") if _HAVE_BS4 else []
    if not emp_rows:
        raw = _find_row(rows, "no. of employees", "number of employees")
        if raw:
            nums = re.findall(r"\d[\d,]*", raw)
            body = [n for n in nums]
            if body:
                emp_rows = [body]
    for cells in emp_rows:
        low = " ".join(cells).lower()
        if "employee male" in low or "management" in low:
            continue  # header row
        if len(cells) >= 3:
            management = clean_int(cells[0])
            male = clean_int(cells[1])
            female = clean_int(cells[2])
        elif len(cells) == 2:
            male, female = clean_int(cells[0]), clean_int(cells[1])
        break

    # -- machines ----------------------------------------------------- #
    machines = clean_int(_find_row(rows, "no of machines", "no. of machines",
                                   "number of machines"))

    # -- production capacity ---------------------------------------- #
    cap_label = ""
    for label, _v in rows:
        if "production capacity" in label.lower() or "export capacity" in label.lower():
            cap_label = label.lower()
            break
    capacity = normalise_capacity(
        _find_row(rows, "production capacity", "export capacity"), cap_label)

    # -- address (prefer the physical factory address) ------------- #
    factory_addr = _address_lines(_find_row(rows, "factory address",
                                            "factory/unit address"))
    mailing_addr = _address_lines(_find_row(rows, "mailling address",
                                            "mailing address"))
    address = ", ".join(factory_addr) or ", ".join(mailing_addr) or None
    if factory_addr:
        pass
    elif mailing_addr:
        notes.append("no factory address on the page; used the mailing address")

    record = {
        "Name of factory": name or None,
        "BGMEA registration no.": reg,
        "Address of factory": address,
        "Factory type (woven, knit, both)": ftype,
        "management": str(management) if management is not None else None,
        "Employee_male": male,
        "Employee_female": female,
        "No. of machines": machines,
        "Production capacity": capacity,
        "_url": url,
    }
    for col in BUSINESS_COLUMNS:
        if record.get(col) in (None, ""):
            notes.append(f"{col}: not published on the page")
    return record, notes
