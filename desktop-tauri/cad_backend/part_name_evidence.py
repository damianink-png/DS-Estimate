"""Read semantic clues from STEP XCAF product names, WITHOUT manufacturing inference.

Part names are untrusted and may be exporter placeholders, stale BOM labels,
parent-assembly names, or refer to HOLES for a fastener rather than the
fastener itself. They never override original B-Rep, automatic stock identity,
cut times, purchase routing, or material. Name evidence is per-occurrence,
never shared between geometrically equivalent parts.
"""
import re
import unicodedata

# These codes identify a family, NOT a complete standard or accepted geometry.
_STANDARDS = {
    ("iso", "4014"): "hex-head", ("iso", "4017"): "hex-head",
    ("din", "931"): "hex-head", ("din", "933"): "hex-head",
    ("iso", "4762"): "socket-head", ("din", "912"): "socket-head",
    ("iso", "4032"): "hex-nut", ("din", "934"): "hex-nut",
    ("iso", "7089"): "washer", ("din", "125"): "washer",
    ("iso", "2338"): "dowel-pin", ("din", "7"): "dowel-pin",
    ("din", "471"): "circlip", ("din", "71412"): "grease-nipple",
}
_KIND_PATTERNS = [
    ("grease-nipple", r"\b(?:smarowniczk\w*|kalamitk\w*|smarownik\w*|grease[\s-]*nipple\w*|schmiernippel\w*)\b"),
    ("bearing", r"\b(?:lozysk\w*|bearing\w*|kugellager\w*)\b"),
    ("circlip", r"\b(?:seger\w*|pierscien[\s-]*osadcz\w*|circlip\w*|retaining[\s-]*ring\w*|sicherungsring\w*)\b"),
    ("washer", r"\b(?:podkladk\w*|washer\w*|unterlegscheib\w*)\b"),
    ("hex-nut", r"\b(?:nakretk\w*|nut|nuts|sechskantmutter\w*|mutter|muttern)\b"),
    ("dowel-pin", r"\b(?:kolek[\s-]*walcow\w*|dowel[\s-]*pin\w*|zylinderstift\w*)\b"),
    ("socket-head", r"\b(?:imbus\w*|socket[\s-]*head\w*|allen[\s-]*bolt\w*|innensechskant\w*)\b"),
    ("hex-head", r"\b(?:hex[\s-]*(?:head[\s-]*)?(?:bolt|screw)\w*|szesciokatn\w*[\s-]*srub\w*|sechskantschraub\w*)\b"),
    ("fastener", r"\b(?:srub\w*|screw\w*|bolt\w*|schraub\w*)\b"),
]
_STOCK_PATTERNS = [
    ("plate", r"\b(?:plyt\w*|blach\w*|plate\w*|blech\w*|sheet[\s-]*metal)\b"),
    ("tube", r"\b(?:rur\w*|tube\w*|pipe\w*|rohr\w*)\b"),
    ("profile", r"\b(?:profil\w*|profile\w*|section\w*|shs|rhs|chs|ipe|heb|hea)\b"),
    ("round-bar", r"\b(?:pret\w*|walek\w*|round[\s-]*bar|rod\w*|welle\w*)\b"),
    ("weldment", r"\b(?:spawan\w*|weldment\w*|schweiss\w*|schweiß\w*)\b"),
]
# A name such as "Bolt hole Ø10" describes a hole in a workpiece, not a bolt.
_PART_FEATURE = re.compile(
    r"\b(?:otwor\w*|hole\w*|bohrung\w*|gewinde[\s-]*bohrung\w*|"
    r"gniazdo|pocket\w*|seat|for|pod|fur|fuer)\b")
_GENERIC = re.compile(
    r"^(?:compound|solid|body|part|shape|unknown|unnamed|assembly|"
    r"bez[\s-]*nazwy|brak[\s-]*nazwy|na[u]?o\d+|"
    r"open[\s-]*cascade[\s-]*step[\s-]*translator\b.*|"
    r"step[\s-]*translator\b.*|=>\s*\[.*\]|"
    r"[0-9.:_ -]+)$")
_METRIC = re.compile(r"(?<![a-z0-9])m\s*(\d{1,2})\s*(?:[x×*]\s*(\d{1,3}(?:[.,]\d+)?))?(?![a-z0-9])")
_NORM = re.compile(r"\b(iso|din)\s*[-_]?\s*(\d{1,5})\b")
_BEARING = re.compile(r"\b(6[023]\d{2})\b")
_DIM = re.compile(r"(?<![a-z0-9])(?:[ø⌀]\s*)?(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)"
                  r"(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?")


def _normalized(value):
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKD", value.casefold()).replace("ł", "l").replace("ß", "ss")
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value).strip()


def parse_part_name(name, name_source="missing"):
    """Return independently reviewable XCAF name evidence, or None.

    Evidence is deliberately unavailable for generic STEP export labels.
    No parse result is a CAD classification, standard-compliance proof,
    or permission to auto-route the part to purchased.
    """
    raw = name if isinstance(name, str) else ""
    text = _normalized(raw)
    if (not text or len(text) > 256 or _GENERIC.fullmatch(text)
            or "open cascade step translator" in text or
            name_source not in ("XCAF occurrence/product", "XCAF occurrence", "XCAF product")):
        return None
    # Detect feature descriptions ("hole for M10 bolt") before family labels.
    # A specific product family cannot be inferred from a feature reference.
    if _PART_FEATURE.search(text) and re.search(
            r"\b(?:srub\w*|bolt\w*|screw\w*|nakretk\w*|nut\w*|washer\w*|podkladk\w*)\b", text):
        return None

    standard_matches = [(m.group(1), m.group(2)) for m in _NORM.finditer(text)]
    families = { _STANDARDS[pair] for pair in standard_matches if pair in _STANDARDS }
    text_family = next((family for family,pat in _KIND_PATTERNS if re.search(pat,text)),None)
    # If a descriptive name disagrees with an explicit standard, don't
    # silently force either one (e.g. "nut ISO 4017").
    conflict = bool(families and text_family and
                    not any(f==text_family or
                            (text_family=="fastener" and f in ("hex-head","socket-head"))
                            for f in families))
    family = None if conflict else (
        next(iter(families)) if len(families)==1
        else text_family if not families else None)
    stock_family = next((k for k,pat in _STOCK_PATTERNS if re.search(pat,text)),None)
    if family is None and stock_family is None and not conflict:
        return None

    metric = _METRIC.search(text)
    designation = None
    if metric:
        size = f"M{int(metric.group(1))}"
        suffix = metric.group(2)
        designation = size + ("x"+suffix.replace(",",".") if suffix else "")
    if family=="bearing":
        b=_BEARING.search(text)
        if b:
            designation=b.group(1)

    # Dimensions without a semantic family are not evidence. For a profile
    # they are only a LABEL, never a measured section/blank.
    dims = None
    if stock_family:
        m=_DIM.search(text)
        if m:
            vals = [v for v in m.groups() if v is not None]
            if len(vals)>=2:
                d=[float(v.replace(",",".")) for v in vals]
                if all(0 < v < 100000 for v in d):
                    dims = d

    result = {
        "status": "name-only-unverified",
        "name": raw.strip(),
        "nameSource": name_source,
        "source": "original STEP XCAF product or occurrence label",
        "limitations": "Name is not proof of B-Rep shape, purchased stock, exact ISO/DIN product, material, operations or price",
    }
    if family:
        result["normaliaFamily"] = family
    if stock_family:
        result["stockFamily"] = stock_family
    if designation:
        result["nominalDesignation"] = designation
    if standard_matches:
        result["standardsMentioned"] = [f"{a.upper()} {b}" for a,b in standard_matches]
    if conflict:
        result["nameConflict"] = "descriptive family contradicts named standard"
    if dims:
        result["nominalDimensionsMm"] = dims
    return result


def compare_name_to_geometry(name_evidence, normalia_hint):
    """One-way name verification. NEVER change CAD result or routing.

    Unreliable / ambiguous names remain unverified. Family / designation
    discrepancies must be visible, not resolved by guessing.
    """
    if not name_evidence or not normalia_hint:
        return None
    if normalia_hint.get("status") != "geometry-candidate":
        return None
    family=name_evidence.get("normaliaFamily")
    label=name_evidence.get("nominalDesignation")
    families=normalia_hint.get("families") or []
    candidates=normalia_hint.get("catalogCandidates") or []
    if name_evidence.get("nameConflict"):
        return {"status":"conflict","reason":"contradictory product name / standard"}
    if family is None and label is None:
        return None
    compatible = (family is None or family in families or
                  (family=="fastener" and any(f in ("hex-head","socket-head") for f in families)))
    if not compatible:
        return {"status":"conflict","reason":"named family differs from original B-Rep family"}
    if label:
        # A thread pitch M6x1 on grease nipples need not appear verbatim in a
        # geometry-only family label. Treat it as unverified, not confirmed.
        if families==["grease-nipple"]:
            return {"status":"family-compatible","reason":"thread and pitch are not modelled in STEP"}
        normalized_designations = [c.get("designation","").casefold().replace("×","x") for c in candidates]
        if label.casefold() not in normalized_designations:
            return {"status":"conflict","reason":"named nominal size differs from measured B-Rep candidate"}
    return {"status":"corroborated" if label else "family-compatible",
            "reason":"name agrees with independent B-Rep candidate; purchase and standard remain unverified"}
