"""Shopify product_type/title 기반 경량 분류기."""

from __future__ import annotations

import re

_GENDER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "men": ("men", "mens", "man", "남성", "맨즈"),
    "women": ("women", "womens", "woman", "여성", "우먼"),
    "kids": ("kids", "kid", "youth", "children", "아동", "키즈"),
}

_SUBCATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shoes": ("shoe", "sneaker", "runner", "boot", "loafer", "sandals", "신발", "슈즈"),
    "outer": ("jacket", "coat", "parka", "blouson", "윈드브레이커", "아우터"),
    "top": ("tee", "t-shirt", "shirt", "knit", "sweat", "hoodie", "셔츠", "상의"),
    "bottom": ("pants", "jean", "trouser", "shorts", "skirt", "하의"),
    "bag": ("bag", "backpack", "tote", "pouch", "가방"),
    "cap": ("cap", "hat", "beanie", "모자"),
    "accessory": ("accessory", "belt", "socks", "wallet", "ring", "bracelet", "액세서리"),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def classify_gender_and_subcategory(
    product_type: str | None,
    title: str,
    tags: str | None = None,
) -> tuple[str | None, str | None]:
    basis = _normalize(" ".join([product_type or "", title or "", tags or ""]))

    gender: str | None = None
    for key, words in _GENDER_KEYWORDS.items():
        if any(word in basis for word in words):
            gender = key
            break
    if gender is None:
        gender = "unisex"

    subcategory: str | None = None
    for key, words in _SUBCATEGORY_KEYWORDS.items():
        if any(word in basis for word in words):
            subcategory = key
            break

    return gender, subcategory
