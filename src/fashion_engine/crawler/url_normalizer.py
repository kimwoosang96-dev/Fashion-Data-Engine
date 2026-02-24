"""
URL 정규화: 상품 페이지 URL → 판매채널 홈페이지 URL
"""
import re
from urllib.parse import urlparse, urlunparse

import tldextract


def normalize_to_homepage(url: str) -> str:
    """
    임의의 URL(상품 페이지, 카테고리 등)을 해당 사이트 홈페이지 URL로 정규화.

    예:
        https://www.musinsa.com/products/3812945 → https://www.musinsa.com
        http://shop.29cm.co.kr/product/detail?... → https://www.29cm.co.kr
    """
    url = url.strip()
    if not url:
        return ""

    # 스키마 없으면 추가
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    extracted = tldextract.extract(url)

    # 서브도메인 처리: shop.xxx.com, m.xxx.com, www.xxx.com → www.xxx.com
    if extracted.subdomain and extracted.subdomain not in ("www", ""):
        # 모바일 서브도메인은 www로 전환
        if extracted.subdomain in ("m", "mobile"):
            host = f"www.{extracted.domain}.{extracted.suffix}"
        else:
            # shop., store. 등 별도 서브도메인은 유지
            host = parsed.netloc
    elif extracted.subdomain == "":
        # 서브도메인 없으면 www 붙임
        host = f"www.{extracted.domain}.{extracted.suffix}"
    else:
        host = parsed.netloc

    # 항상 https로 통일
    return urlunparse(("https", host, "", "", "", ""))


def extract_domain(url: str) -> str:
    """중복 판단용 도메인 추출 (서브도메인 무시)"""
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}".lower()


def guess_channel_name(url: str) -> str:
    """URL에서 채널명 추론 (초기 전처리용)"""
    extracted = tldextract.extract(url)
    name = extracted.domain
    # camelCase나 kebab-case를 공백으로 분리
    name = re.sub(r"[-_]", " ", name)
    return name.title()


def classify_channel_type(url: str) -> str:
    """
    URL 패턴으로 채널 타입 1차 분류.
    브랜드 공식몰: URL이 단일 브랜드명과 일치
    마켓플레이스: 무신사, W컨셉 등 키워드
    """
    known_marketplaces = {
        "musinsa", "wconcept", "29cm", "hnmfashion", "hm",
        "zalando", "asos", "ssense", "farfetch", "mytheresa",
        "kream", "lotte", "hyundaihmall", "ssg", "lfmall",
    }
    known_multibrand = {
        "ounce", "roundabout", "handsome", "thehandsome",
    }

    extracted = tldextract.extract(url)
    domain = extracted.domain.lower()

    if domain in known_marketplaces:
        return "marketplace"
    if domain in known_multibrand:
        return "multi-brand"
    return "unknown"
