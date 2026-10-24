"""Üç çıkarım yolu (PLAN.md): A görsel + bulanık eşleme, B OCR kimlik alıntısı, C görsel + OCR kimlik alıntısı."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from rapidfuzz import fuzz

from ortak import CALISMA, Belge, Kelime, alan_adi, birlesim, normalize

CLAUDE = shutil.which("claude")
ISCI_DIZIN = Path(tempfile.gettempdir()) / "citefield-s1-isci"
ISCI_DIZIN.mkdir(exist_ok=True)

CIKTI = ('Return ONLY a JSON object, no prose: {"fields": [{"field": "<field name>", "value": "<value exactly as printed>"%s}]}. '
         "Emit one entry per occurrence (each line item separately). Omit fields that are not present.")


def ocr_metni(kelimeler: list[Kelime]) -> str:
    satirlar: dict[tuple, list[Kelime]] = {}
    for k in kelimeler:
        satirlar.setdefault(k.satir, []).append(k)
    return "\n".join(" ".join(f"[{k.id}]{k.text}" for k in ks) for ks in satirlar.values())


def istem(yol: str, belge: Belge, kelimeler: list[Kelime], sema: str) -> str:
    bas = f"You extract structured fields from a document. Schema fields: {sema}.\n"
    if yol == "A":
        return bas + f"Read the document image at {belge.resim.as_posix()}.\n" + CIKTI % ""
    ocr = ("OCR words of the document, one OCR line per row, each word prefixed with its id in brackets:\n"
           + ocr_metni(kelimeler) + "\n")
    alinti = ', "word_ids": [<ids of the OCR words this value was read from>]'
    if yol == "B":
        return bas + ocr + "If OCR misread a character, give the corrected value but still cite the word ids.\n" + CIKTI % alinti
    return (bas + f"Read the document image at {belge.resim.as_posix()} and use the OCR words below to cite where each "
            "value is located. If OCR misread a character, give the value as printed in the image but still cite the word ids.\n"
            + ocr + CIKTI % alinti)


def claude(prompt: str, gorsel: bool) -> str:
    komut = [CLAUDE, "-p", "--model", "sonnet", "--output-format", "json"]
    komut += ["--allowedTools", "Read", "--add-dir", str(CALISMA / "resim")] if gorsel else ["--tools", ""]
    env = dict(os.environ, PROJE_SISTEMI_INVOKED_BY="citefield-s1", PYTHONUTF8="1")
    r = subprocess.run(komut, input=prompt.encode("utf-8"), capture_output=True, cwd=ISCI_DIZIN, env=env, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-500:])
    return json.loads(r.stdout.decode("utf-8"))["result"]


def json_ayikla(metin: str) -> list[dict]:
    """İlk geçerli JSON nesnesini okur; model arkasına ikinci bir blok ya da açıklama eklese de bozulmaz."""
    i = metin.find("{")
    while i != -1:
        try:
            nesne, _ = json.JSONDecoder().raw_decode(metin, i)
            if isinstance(nesne, dict) and "fields" in nesne:
                return nesne["fields"]
        except json.JSONDecodeError:
            pass
        i = metin.find("{", i + 1)
    return []


def bulanik_kutu(deger: str, kelimeler: list[Kelime], kullanilan: set[int]):
    """Değere en çok benzeyen ardışık OCR kelime dizisi (en fazla 8 kelime)."""
    hedef = normalize(deger)
    if not hedef:
        return None, 0.0
    en_iyi, skor = None, 0.0
    for i in range(len(kelimeler)):
        metin = ""
        for j in range(i, min(i + 8, len(kelimeler))):
            metin += normalize(kelimeler[j].text)
            s = fuzz.ratio(metin, hedef) - (5 if any(k in kullanilan for k in range(i, j + 1)) else 0)
            if s > skor:
                en_iyi, skor = (i, j), s
            if len(metin) > len(hedef) * 1.5:
                break
    if en_iyi is None:
        return None, 0.0
    kullanilan.update(range(en_iyi[0], en_iyi[1] + 1))
    return birlesim(kelimeler[k].kutu for k in range(en_iyi[0], en_iyi[1] + 1)), skor


def tahminler(yol: str, belge: Belge, kelimeler: list[Kelime], sema: str) -> list[dict]:
    on = CALISMA / "cikti" / f"{yol}-{belge.kimlik}.json"
    if on.exists():
        ham = on.read_text("utf-8")
    else:
        ham = claude(istem(yol, belge, kelimeler, sema), gorsel=yol in "AC")
        on.parent.mkdir(parents=True, exist_ok=True)
        on.write_text(ham, "utf-8")
    alanlar = json_ayikla(ham)
    out, kullanilan = [], set()
    idx = {k.id: k for k in kelimeler}
    for a in alanlar:
        t = {"alan": alan_adi(a.get("field")), "deger": str(a.get("value", ""))}
        if yol == "A":
            t["kutu"], t["eslesme"] = bulanik_kutu(t["deger"], kelimeler, kullanilan)
        else:
            ids = [i for i in a.get("word_ids") or [] if i in idx]
            t["kutu_ham"] = birlesim(idx[i].kutu for i in ids) if ids else None
            # Alıntı doğrulama: yalnız değerin içinde geçen kelimeler kutuya girer (etiket kelimesi düşer).
            hedef = normalize(t["deger"])
            icinde = [i for i in ids if normalize(idx[i].text) and normalize(idx[i].text) in hedef]
            t["alinti_uyumu"] = bool(ids) and len(icinde) == len(ids)
            secilen = icinde or ids
            t["kutu"] = birlesim(idx[i].kutu for i in secilen) if secilen else None
        out.append(t)
    return out
