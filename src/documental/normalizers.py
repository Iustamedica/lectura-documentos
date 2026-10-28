"""Normalizadores de datos chilenos usados por todos los extractores.

Todo lo que se extrae por OCR llega sucio (espacios, puntos, letras confundidas
con digitos). Aqui se concentran las funciones que convierten ese texto en
valores estructurados y verificables.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable

# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------

# El OCR confunde sistematicamente algunos caracteres en documentos escaneados.
OCR_CHAR_MAP = str.maketrans(
    {
        "|": "I",
        "¦": "I",
        "¡": "1",
        "º": "o",
        "ª": "a",
        "°": "o",
    }
)


def strip_accents(text: str) -> str:
    """Quita tildes y dieresis (util para comparar palabras clave)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


def fold(text: str) -> str:
    """Normaliza a minusculas, sin tildes y con espacios colapsados.

    Es la forma canonica usada para comparar contra palabras clave.
    """
    return re.sub(r"\s+", " ", strip_accents(text or "")).strip().lower()


def squeeze(text: str) -> str:
    """Colapsa espacios multiples sin alterar mayusculas ni tildes."""
    return re.sub(r"[ \t\u00a0]+", " ", text or "").strip()


def clean_name(text: str) -> str:
    """Limpia un nombre de persona o razon social conservando tildes.

    - Elimina prefijos frecuentes del OCR ("Sr(a):", "Beneficiario(a):").
    - Elimina caracteres de relleno de puntos guia.
    - Colapsa espacios.
    """
    value = squeeze(text or "")
    value = re.sub(r"^[\s:.\-\u2013]+", "", value)
    value = re.sub(r"[.\u00b7]{2,}\s*$", "", value)
    value = value.strip(" .:-\u2013")
    return value


def title_case_name(name: str) -> str:
    """Deja el nombre en mayusculas sostenidas tal como aparece en los documentos.

    Los documentos FONASA usan MAYUSCULAS; se respeta el original para no
    inventar formato. Solo se normaliza el espaciado.
    """
    return squeeze(name).upper()


# --------------------------------------------------------------------------
# RUT chileno
# --------------------------------------------------------------------------

_RUT_CANDIDATE = re.compile(r"(\d{1,3}(?:[.\s]?\d{3}){0,2}|\d{6,9})\s*-\s*([0-9kK])")
# Variante tolerante: el OCR a veces deja el punto de miles en posiciones raras
# ("78.00692-7"), por lo que se aceptan digitos mezclados con puntos y se limpian.
_RUT_TOLERANT = re.compile(r"(\d[\d.\s]{4,14}\d)\s*-\s*([0-9kK])")
_RUT_BARE = re.compile(r"\b(\d{7,8})([0-9kK])\b")


def rut_dv(body: int) -> str:
    """Calcula el digito verificador de un RUT (modulo 11)."""
    total = 0
    multiplier = 2
    for digit in reversed(str(body)):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    remainder = 11 - (total % 11)
    if remainder == 11:
        return "0"
    if remainder == 10:
        return "K"
    return str(remainder)


def format_rut(body: int, dv: str) -> str:
    """Formatea un RUT como 12.345.678-9."""
    digits = str(body)
    grouped = ""
    while len(digits) > 3:
        grouped = "." + digits[-3:] + grouped
        digits = digits[:-3]
    grouped = digits + grouped
    return f"{grouped}-{dv.upper()}"


def parse_rut(text: str, *, validate: bool = True) -> str | None:
    """Extrae y normaliza el primer RUT valido que aparezca en `text`.

    Devuelve el RUT en formato 12.345.678-9 o None si no hay ninguno.
    Con `validate=True` se exige que el digito verificador sea correcto, lo
    que elimina practicamente todos los falsos positivos del OCR.
    """
    if not text:
        return None
    candidate_text = text.translate(OCR_CHAR_MAP)
    for pattern in (_RUT_CANDIDATE, _RUT_TOLERANT):
        for match in pattern.finditer(candidate_text):
            body_raw, dv = match.group(1), match.group(2)
            digits = re.sub(r"\D", "", body_raw)
            if not digits:
                continue
            body = int(digits)
            if not 1_000_000 <= body <= 99_999_999:
                continue
            if validate and rut_dv(body) != dv.upper():
                continue
            return format_rut(body, dv)
    if not validate:
        for match in _RUT_BARE.finditer(candidate_text):
            body = int(match.group(1))
            if 1_000_000 <= body <= 99_999_999:
                return format_rut(body, match.group(2))
    return None


def rut_body(rut: str | None) -> int | None:
    """Devuelve solo el cuerpo numerico de un RUT formateado."""
    if not rut:
        return None
    digits = re.sub(r"\D", "", rut.split("-")[0])
    return int(digits) if digits else None


def find_all_ruts(text: str, *, validate: bool = True) -> list[str]:
    """Devuelve todos los RUT distintos (en orden de aparicion) de un texto."""
    found: list[str] = []
    for chunk in re.findall(r"\d[\d.\s]{5,12}-\s*[0-9kK]", text or ""):
        rut = parse_rut(chunk, validate=validate)
        if rut and rut not in found:
            found.append(rut)
    return found


# --------------------------------------------------------------------------
# Montos en pesos
# --------------------------------------------------------------------------

_AMOUNT = re.compile(r"(\d{1,3}(?:[.\s]\d{3})+|\d{1,7})(?![\d])")


def parse_clp(text: str | None) -> int | None:
    """Convierte un monto chileno en entero.

    Acepta 20.000, 20 000, $20.000, 20000, $0 y 111.860.
    Devuelve None cuando el texto no contiene ningun numero.
    """
    if text is None:
        return None
    cleaned = re.sub(r"[$S]", "", str(text)).strip()
    match = _AMOUNT.search(cleaned)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    if not digits:
        return None
    value = int(digits)
    return value if value <= 99_999_999 else None


def format_clp(value: int | None) -> str:
    """Formatea un entero como $20.000."""
    if value is None:
        return ""
    return "$" + f"{value:,}".replace(",", ".")


# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------

_MONTHS_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_DATE_ISO = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
_DATE_NUM = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b")
_DATE_LONG = re.compile(
    r"(\d{1,2})\s*(?:de\s+)?([-/. ]?)([a-zA-Záéíóú]{3,10})\.?\s*(?:de\s+|[-/]\s*)?(\d{4})\b",
    re.IGNORECASE,
)


def _safe_date(year: int, month: int, day: int) -> date | None:
    if year < 100:
        year += 2000 if year < 70 else 1900
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    if not 1990 <= year <= 2100:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date(text: str | None) -> date | None:
    """Extrae la primera fecha valida de un texto en formatos chilenos.

    Soporta 29-09-2026, 29/09/2026, 29.09.2026, 2026-09-29,
    24 de octubre de 2025 y 25-mar-2024.
    """
    if not text:
        return None

    for match in _DATE_ISO.finditer(text):
        found = _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if found:
            return found

    for match in _DATE_LONG.finditer(text):
        month_name = strip_accents(match.group(3)).lower()
        month = _MONTHS_ES.get(month_name) or (
            _MONTHS_ES.get(month_name[:3]) if len(month_name) > 3 else None
        )
        if month:
            found = _safe_date(int(match.group(4)), month, int(match.group(1)))
            if found:
                return found

    for match in _DATE_NUM.finditer(text):
        found = _safe_date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        if found:
            return found
    return None


def parse_time(text: str | None) -> str | None:
    """Extrae la primera hora HH:MM(:SS) de un texto."""
    if not text:
        return None
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b", text)
    if not match:
        return None
    hh, mm, ss = match.group(1), match.group(2), match.group(3)
    return f"{int(hh):02d}:{mm}" + (f":{ss}" if ss else "")


def date_to_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def format_date_cl(value: date | None) -> str:
    return value.strftime("%d-%m-%Y") if value else ""


# --------------------------------------------------------------------------
# Utilidades de busqueda en texto de OCR
# --------------------------------------------------------------------------


def first_match(patterns: Iterable[str], text: str, *, flags: int = re.IGNORECASE) -> str | None:
    """Devuelve el primer grupo capturado (grupo 1) de los patrones dados."""
    for pattern in patterns:
        match = re.search(pattern, text or "", flags)
        if match:
            value = (match.group(1) if match.groups() else match.group(0)).strip(" :.-")
            if value:
                return value
    return None


def looks_like_person_name(text: str) -> bool:
    """Heuristica: 2 a 6 palabras alfabeticas, sin digitos ni palabras de formulario."""
    value = clean_name(text)
    if not value or any(ch.isdigit() for ch in value):
        return False
    words = [w for w in re.split(r"\s+", value) if w]
    if not 2 <= len(words) <= 6:
        return False
    blacklist = {
        "rut", "fecha", "total", "valor", "neto", "iva", "boleta", "bono", "detalle",
        "descripcion", "cantidad", "precio", "direccion", "comuna", "contacto",
    }
    if any(fold(w) in blacklist for w in words):
        return False
    return all(re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ.'-]+", w) for w in words)


# --------------------------------------------------------------------------
# Validacion de nombres manuscritos
# --------------------------------------------------------------------------

# Silabas y fragmentos frecuentes en nombres y apellidos chilenos. El OCR de
# texto manuscrito produce cadenas como "MAMAGLORIA CAMWAM AOY" o "CoevogeD Mego"
# que son alfabeticas pero no son nombres; esta lista permite descartarlas.
_NAME_HINTS = (
    "maria", "jose", "juan", "carlos", "alberto", "gloria", "ester", "ana", "luis",
    "luisa", "pedro", "pablo", "diego", "rodrigo", "andres", "andrea", "carolina",
    "francisco", "francisca", "manuel", "manuel", "rosa", "carmen", "elena",
    "patricia", "marcela", "claudia", "veronica", "alejandra", "gabriela",
    "gonzalez", "munoz", "rojas", "diaz", "perez", "vargas", "molina", "soto",
    "contreras", "silva", "martinez", "sepulveda", "morales", "rodriguez",
    "lopez", "fuentes", "hernandez", "torres", "aravena", "flores", "espinoza",
    "valdes", "castillo", "tapia", "reyes", "gutierrez", "castro", "pizarro",
    "segura", "velasquez", "orellana", "nunez", "jara", "vergara", "rivera",
)


def _se_parece(palabra: str, referencia: str) -> bool:
    """True si la palabra se parece a un nombre conocido (no solo lo contiene).

    El OCR de manuscrito pega palabras ("MAMAGLORIA"), por lo que se acepta que
    la referencia este contenida en la palabra, pero solo si la diferencia es
    pequena (hasta 4 caracteres de ruido a cada lado) o si la palabra es corta.
    """
    if len(palabra) == len(referencia):
        return palabra == referencia
    if palabra.startswith(referencia) or palabra.endswith(referencia):
        return len(palabra) - len(referencia) <= 3
    return False


def plausible_person_name(text: str, *, min_hits: int = 1) -> bool:
    """True si el texto parece realmente un nombre de persona.

    Combina la validacion estructural de `looks_like_person_name`, el rechazo de
    etiquetas de formulario ("DATOS PERSONA BENEFICIARIA") y una comprobacion de
    contenido: al menos `min_hits` palabras deben parecerse a un nombre o apellido
    conocido. Asi se descarta el ruido del OCR de letra manuscrita
    ("MAMAGLORIA CAMWAM AOY") sin perder nombres reales.
    """
    if looks_like_form_label(text):
        return False
    if not looks_like_person_name(text):
        return False
    palabras = [fold(w) for w in clean_name(text).split() if len(w) >= 3]
    if not palabras:
        return False
    aciertos = sum(
        1 for palabra in palabras if any(_se_parece(palabra, hint) for hint in _NAME_HINTS)
    )
    return aciertos >= min_hits


# --------------------------------------------------------------------------
# Ayudas para distinguir RUT de personas de RUT de empresas/profesionales
# --------------------------------------------------------------------------

# En Chile los RUT de personas naturales son inferiores a 30 millones; los de
# empresas (SPA, LTDA, fundaciones, clinicas) parten sobre los 65 millones y los
# mas antiguos (sociedades de profesionales) sobre los 50 millones.
PERSON_RUT_MAX_BODY = 30_000_000

# Etiquetas que, al aparecer junto a un RUT, indican que ese RUT NO es del
# paciente/titular (emisor, prestador, profesional, institucion impresora...).
NON_PATIENT_RUT_LABELS = (
    "rut prestador", "rut profesional", "rut tratante", "rut emisor", "rut medico",
    "rut institucion", "rut establecimiento", "rut valorizador", "rut empresa",
    "rut representante", "rut doctor", "rut dr", "rut dra", "rut tecnico",
    "r.u.t. imp", "codina imp", "imp. ltda", "imprenta",
)

# Elementos de formulario que no son nombres de persona.
_NOT_A_NAME = {
    "datos de prestador", "datos de beneficiario", "datos de beneficiaria",
    "datos persona beneficiaria", "financiamiento emisor", "copia cliente",
    "venta exenta", "directamente al paciente", "presupuesto",
    "nombre social", "datos de prestador(a)", "datos de prestador a",
    "nombre registral", "datos del paciente", "datos del beneficiario",
    "identificacion del paciente", "nombre del paciente", "datos personales",
}


def is_person_rut(rut: str | None) -> bool:
    """True si el RUT corresponde (probablemente) a una persona natural."""
    body = rut_body(rut)
    return bool(body and body < PERSON_RUT_MAX_BODY)


def rut_label_context(text: str, rut: str) -> str:
    """Texto inmediatamente anterior a un RUT, para saber a quien pertenece.

    Se conservan los espacios (las etiquetas son palabras separadas) y solo se
    eliminan puntos y guiones del RUT para localizarlo en el texto.
    """
    if not rut:
        return ""
    digits = re.sub(r"\D", "", rut.split("-")[0])
    # Se localiza el RUT en el texto sin puntos para tolerar "12.345.678-5" vs
    # "12345678-5", pero el recorte del contexto se hace sobre el texto original.
    compacto = re.sub(r"[.\s]", "", text or "")
    posicion = compacto.find(digits)
    if posicion < 0:
        return fold(text or "")[:80]
    acumulado = 0
    corte = 0
    for i, ch in enumerate(text or ""):
        if acumulado >= posicion:
            corte = i
            break
        if not ch.isspace() and ch != ".":
            acumulado += 1
    return fold((text or "")[:corte])[-60:]


def rut_is_prestador(text: str, rut: str) -> bool:
    """True si el RUT aparece asociado a emisor/prestador/profesional."""
    contexto = rut_label_context(text, rut)
    return any(label in contexto for label in NON_PATIENT_RUT_LABELS)


def looks_like_form_label(text: str) -> bool:
    """True si el texto es una etiqueta de formulario, no un nombre de persona."""
    return fold(text).strip(" :.-") in _NOT_A_NAME


_ROMAN_TABLE = (("M", 1000), ("CM", 900), ("D", 500), ("CD", 400), ("C", 100),
                ("XC", 90), ("L", 50), ("XL", 40), ("X", 10), ("IX", 9),
                ("V", 5), ("IV", 4), ("I", 1))


def _leer_romano(texto: str) -> int | None:
    """Convierte numeros romanos simples (I a XXXIX) a entero."""
    if not texto or not re.fullmatch(r"[IVXLC]+", texto.upper()):
        return None
    resto, total = texto.upper(), 0
    for simbolo, valor in _ROMAN_TABLE:
        while resto.startswith(simbolo):
            total += valor
            resto = resto[len(simbolo):]
    return total if 0 < total < 100 else None


def roman_letters_to_digits(text: str) -> str:
    """Corrige digitos leidos como letras romanas en una fecha.

    El OCR confunde con frecuencia "1" con "I" y "0" con "O" dentro de fechas
    ("4-0I-2026" -> "4-01-2026"). Solo se aplican las conversiones que dejan como
    resultado una fecha valida; si no, se devuelve el texto original intacto.
    """
    if not text:
        return text

    def _intentar(valor: str) -> str | None:
        return valor if parse_date(valor) else None

    # 1) Dia o mes escrito con numerales romanos: "25-XII-2025" -> "25-12-2025"
    for match in re.finditer(r"(?<=\d-)([IVXLCivxlc]{1,4})(?=-)", text):
        numero = _leer_romano(match.group(1))
        if not numero:
            continue
        candidato = text[: match.start()] + f"{numero:02d}" + text[match.end():]
        if _intentar(candidato):
            text = candidato
            break

    # 2) Confusiones letra/numero dentro de una fecha numerica: "0I" -> "01".
    for sospechoso in re.finditer(r"[0-9OIl|]{1,2}[-/.][0-9OIl|]{1,2}[-/.][0-9OIl|]{2,5}", text):
        fragmento = sospechoso.group(0)
        corregido = fragmento
        for origen, destino in (("I", "1"), ("l", "1"), ("|", "1"), ("O", "0")):
            corregido = corregido.replace(origen, destino)
        # El dia y el mes se normalizan a dos digitos ("4" -> "04").
        partes = re.split(r"([-/])", corregido)
        if len(partes) >= 5:
            partes[0] = partes[0].zfill(2)
            partes[2] = partes[2].zfill(2)
            # Un año con mas de cuatro digitos ("20026") suele ser un digito
            # duplicado al inicio o al final; los ultimos cuatro son el año.
            if len(partes[4]) > 4 and partes[4].isdigit():
                partes[4] = partes[4][-4:]
            corregido = "".join(partes)
        candidato = text.replace(fragmento, corregido)
        if _intentar(candidato):
            text = candidato
            break
    return text


def name_tokens(text: str) -> list[str]:
    """Palabras significativas de un nombre (3+ letras, sin tildes)."""
    return re.findall(r"[a-zñ]{3,}", fold(text or ""))


def _fuzzy_share(nombre: str, observado: str, *, max_ruido: int = 3) -> int:
    """Cuenta palabras del nombre que aparecen en el texto, aun pegadas.

    El OCR de manuscrito une palabras ("MAMAGLORIA" contiene "gloria"), por lo que
    la comparacion exacta de tokens no basta. Se acepta una palabra del nombre si
    aparece contenida en el texto con a lo mas `max_ruido` letras de diferencia.
    """
    texto = " " + re.sub(r"[^a-zñ ]", " ", fold(observado or "")) + " "
    compacto = texto.replace(" ", "")
    aciertos = 0
    for token in set(name_tokens(nombre)):
        if f" {token} " in texto:
            aciertos += 1
            continue
        if token in compacto and len(token) >= 4:
            aciertos += 1
            continue
        # Distancia de edicion minima contra ventanas de texto similar.
        for inicio in range(0, max(1, len(compacto) - len(token) + 1)):
            ventana = compacto[inicio : inicio + len(token) + max_ruido]
            if _se_parece(ventana, token):
                aciertos += 1
                break
    return aciertos


def names_overlap(a: str, b: str, *, min_shared: int = 2) -> bool:
    """True si dos textos de nombre comparten al menos `min_shared` palabras."""
    words_a = set(name_tokens(a))
    words_b = set(name_tokens(b))
    if len(words_a & words_b) >= min_shared:
        return True
    return _fuzzy_share(a, b) >= min_shared

