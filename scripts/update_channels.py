"""
channels_cleaned.csv 에 이름/국가/채널타입을 일괄 업데이트.

채널 타입:
  brand-store   = 브랜드 자체 판매 페이지
  edit-shop     = 편집샵 (멀티브랜드 큐레이션)
  department-store / secondhand-marketplace / non-fashion = 기존 유지
"""
import csv
from pathlib import Path

# URL(정규화된 홈페이지 URL) → (clean_name, country, channel_type)
MAPPING: dict[str, tuple[str, str, str]] = {
    # ── 대한민국 ────────────────────────────────────────────────────
    "https://www.thegreatalfred.com":    ("Alfred",                "KR", "edit-shop"),
    "https://www.meclads.com":           ("Meclads",               "KR", "edit-shop"),
    "https://www.openershop.co.kr":      ("Openershop",            "KR", "edit-shop"),
    "https://www.empty.seoul.kr":        ("empty",                 "KR", "edit-shop"),
    "https://www.addictedseoul.com":     ("ADDICTED",              "KR", "edit-shop"),
    "https://www.8division.com":         ("8DIVISION",             "KR", "edit-shop"),
    "https://www.thisisneverthat.com":   ("thisisneverthat",       "KR", "brand-store"),
    "https://www.adressershop.com":      ("a.dresser",             "KR", "edit-shop"),
    "https://www.obscura-store.com":     ("obscura",               "KR", "edit-shop"),
    "https://www.mode-man.com":          ("MODE MAN",              "KR", "edit-shop"),
    "https://www.thexshop.co.kr":        ("THEXSHOP",              "KR", "edit-shop"),
    "https://www.cayl.co.kr":            ("CAYL",                  "KR", "brand-store"),
    "https://www.sculpstore.com":        ("SCULP STORE",           "KR", "edit-shop"),
    "https://www.bizzare.co.kr":         ("BIZZARE",               "KR", "edit-shop"),
    "https://www.breche-online.com":     ("브레슈 (Breche)",        "KR", "brand-store"),
    "https://www.grds.com":              ("grds",                  "KR", "edit-shop"),
    "https://www.heritagefloss.com":     ("heritagefloss",         "KR", "brand-store"),
    "https://www.etcseoul.com":          ("ETC SEOUL",             "KR", "edit-shop"),
    "https://www.ecru.co.kr":            ("ECRU Online",           "KR", "edit-shop"),
    "https://www.rinostore.co.kr":       ("Rino Store",            "KR", "edit-shop"),
    "https://www.082plus.com":           ("082plus",               "KR", "brand-store"),
    "https://www.coevo.com":             ("COEVO",                 "KR", "edit-shop"),
    "https://www.sunchambersociety.com": ("Sun Chamber Society",   "KR", "brand-store"),
    "https://gooutstore.cafe24.com":     ("GOOUTSTORE",            "KR", "edit-shop"),
    "https://www.unipair.com":           ("Unipair",               "KR", "edit-shop"),
    "https://www.adekuver.com":          ("ADEKUVER",              "KR", "edit-shop"),
    "https://www.parlour.kr":            ("PARLOUR",               "KR", "edit-shop"),
    "https://www.bluesman.co.kr":        ("블루스맨 (Bluesman)",    "KR", "edit-shop"),
    "https://www.effortless-store.com":  ("EFFORTLESS",            "KR", "edit-shop"),
    "https://www.kasina.co.kr":          ("Kasina",                "KR", "edit-shop"),
    "https://www.noclaim.co.kr":         ("NOCLAIM",               "KR", "edit-shop"),
    "https://www.nightwaks.com":         ("nightwaks",             "KR", "brand-store"),
    "https://www.casestudystore.co.kr":  ("Casestudy",             "KR", "edit-shop"),
    "https://www.applixy.com":           ("APPLIXY",               "KR", "edit-shop"),
    "https://www.tune.kr":               ("TUNE.KR",               "KR", "edit-shop"),

    # ── 미국 ────────────────────────────────────────────────────────
    "https://www.weareallhumans.com":    ("weareallhumans",        "US", "brand-store"),
    "https://family.d-r-g-n.com":       ("D-R-G-N",               "US", "brand-store"),
    "https://www.luu-dan.com":           ("LU'U DAN",              "US", "brand-store"),
    "https://www.cherryla.com":          ("CHERRY LA",             "US", "edit-shop"),
    "https://www.twofrogsofficial.com":  ("Two Frogs",             "US", "brand-store"),
    "https://www.greats.com":            ("GREATS",                "US", "brand-store"),
    "https://www.hlorenzo.com":          ("H. Lorenzo",            "US", "edit-shop"),
    "https://www.brotherbrother.us":     ("Brother Brother",       "US", "edit-shop"),
    "https://www.thelooprunning.com":    ("The Loop Running Supply","US", "edit-shop"),
    "https://www.golfwang.com":          ("GOLF WANG",             "US", "brand-store"),
    "https://www.joefreshgoods.com":     ("Joe Freshgoods",        "US", "brand-store"),
    "https://www.warrenlotas.com":       ("Warren Lotas",          "US", "brand-store"),
    "https://kr.stussy.com":             ("Stüssy",                "US", "brand-store"),
    "https://www.skyhighfarmgoods.com":  ("Sky High Farm Goods",   "US", "brand-store"),
    "https://www.18east.co":             ("18 East",               "US", "brand-store"),

    # ── 일본 ────────────────────────────────────────────────────────
    "https://www.unexpected-store.com":          ("unexpected store",           "JP", "edit-shop"),
    "https://www.lttt.life":                     ("LTTT",                       "JP", "brand-store"),
    "https://www.wegenk.com":                    ("wegenk",                     "JP", "edit-shop"),
    "https://www.maisonshunishizawa.online":      ("MaisonShunIshizawa store",   "JP", "brand-store"),
    "https://www.plus81.id":                     ("+81",                        "JP", "edit-shop"),
    "https://www.birthoftheteenager.com":         ("BoTT",                       "JP", "brand-store"),
    "https://store.jb-voice.co.jp":              ("JACK in the NET",            "JP", "edit-shop"),
    "https://www.acrmtsm.jp":                    ("ACRMTSM",                    "JP", "brand-store"),
    "https://www.goldwin-global.com":            ("Goldwin",                    "JP", "brand-store"),
    "https://store.digawel.com":                 ("DIGAWEL",                    "JP", "brand-store"),
    "https://www.thenatures.jp":                 ("THE NATURES",                "JP", "edit-shop"),
    "https://www.southstore-online.com":         ("SOUTH STORE",                "JP", "edit-shop"),
    "https://www.new-light-okinawa.com":         ("NƏW LIGHT",                  "JP", "edit-shop"),
    "https://www.rogues.co.jp":                  ("Rogues",                     "JP", "edit-shop"),
    "https://elephab.buyshop.jp":                ("elephant TRIBAL fabrics",    "JP", "brand-store"),
    "https://www.kerouac.okinawa":               ("Kerouac",                    "JP", "edit-shop"),
    "https://www.clesste.com":                   ("CLESSTE",                    "JP", "brand-store"),
    "https://www.liberaiders.jp":                ("Liberaiders",                "JP", "brand-store"),
    "https://shop.pheb.jp":                      ("앤드헵 (Pheb)",               "JP", "edit-shop"),
    "https://www.markaware.jp":                  ("MARKAWARE",                  "JP", "brand-store"),
    "https://shop.ciota.jp":                     ("CIOTA",                      "JP", "brand-store"),
    "https://www.musterwerk-sud.com":            ("MusterWerk",                 "JP", "edit-shop"),
    "https://tity.ocnk.net":                     ("TITY",                       "JP", "edit-shop"),
    "https://www.blackeyepatch.com":             ("BlackEyePatch",              "JP", "brand-store"),
    "https://www.tttmsw.jp":                     ("TTTMSW",                     "JP", "brand-store"),
    "https://www.brownieonline.jp":              ("browniegift",                "JP", "edit-shop"),
    "https://someit.stores.jp":                  ("SOMEIT",                     "JP", "brand-store"),
    "https://www.pherrows.tokyo":                ("Pherrow's",                  "JP", "brand-store"),
    "https://www.faze-one.com":                  ("fazeone",                    "JP", "edit-shop"),
    "https://www.yoketokyo.com":                 ("YOKE",                       "JP", "brand-store"),
    "https://shop.evisenskateboards.com":        ("Evisen Skateboards",         "JP", "brand-store"),
    "https://www.srd-osaka.com":                 ("SHRED",                      "JP", "edit-shop"),
    "https://www.f-lagstuf-f.com":               ("F-LAGSTUF-F",                "JP", "brand-store"),
    "https://www.11747391.net":                  ("11747391",                   "JP", "brand-store"),
    "https://shop.tightbooth.com":               ("TIGHTBOOTH",                 "JP", "brand-store"),
    "https://www.room-onlinestore.jp":           ("ROOM ONLINE STORE",          "JP", "edit-shop"),
    "https://shop.cocorozashi.jp":               ("cocorozashi",                "JP", "edit-shop"),
    "https://asia.freshservice.jp":              ("FreshService",               "JP", "brand-store"),
    "https://www.rocky-mountain-featherbed.com": ("Rocky Mountain Featherbed",  "JP", "brand-store"),
    "https://www.process-store.com":             ("process",                    "JP", "edit-shop"),
    "https://www.pan-kanazawa.com":              ("PAN KANAZAWA",               "JP", "edit-shop"),
    "https://laidback0918.shop-pro.jp":          ("Laid back",                  "JP", "edit-shop"),
    "https://jp.mercari.com":                    ("Mercari (메루카리)",           "JP", "secondhand-marketplace"),
    "https://global.baloriginal.com":            ("baloriginal",                "JP", "brand-store"),
    "https://www.coverchord.com":                ("COVERCHORD",                 "JP", "edit-shop"),
    "https://kr.grounds-fw.com":                 ("grounds",                    "JP", "edit-shop"),
    "https://www.afb-afb-afb.com":               ("AFB",                        "JP", "edit-shop"),
    "https://www.bluemonte.store":               ("Blue Monte",                 "JP", "edit-shop"),
    "https://www.fascinate-online.com":          ("FASCINATE",                  "JP", "edit-shop"),
    "https://www.arknets.co.jp":                 ("ARKnets",                    "JP", "edit-shop"),
    "https://www.attic-sendai.com":              ("Attic",                      "JP", "edit-shop"),
    "https://www.therealmccoys.jp":              ("The Real McCoy's",           "JP", "brand-store"),
    "https://www.corneliantaurus.com":           ("cornelian taurus",           "JP", "brand-store"),
    "https://undercoverk.theshop.jp":            ("UNDERCOVER Kanazawa",        "JP", "edit-shop"),
    "https://www.nubiantokyo.com":               ("NUBIAN",                     "JP", "edit-shop"),
    "https://www.tinyworld.jp":                  ("TINY OSAKA",                 "JP", "edit-shop"),
    "https://www.anachronorm.jp":                ("ANACHRONORM",                "JP", "brand-store"),
    "https://www.hideandseekstore.com":          ("hideandseekStore",           "JP", "brand-store"),
    "https://www.baycrews.jp":                   ("BAYCREW'S",                  "JP", "department-store"),
    "https://www.fce-store.com":                 ("F/CE",                       "JP", "brand-store"),
    "https://www.andwander.co.kr":               ("and wander",                 "JP", "brand-store"),

    # ── 영국 ────────────────────────────────────────────────────────
    "https://www.storymfg.com":          ("Story mfg.",            "UK", "brand-store"),
    "https://www.thehipstore.co.uk":     ("HIP",                   "UK", "edit-shop"),
    "https://www.harrods.com":           ("Harrods",               "UK", "department-store"),
    "https://www.corteiz.com":           ("Corteiz",               "UK", "brand-store"),
    "https://www.about---blank.com":     ("about:blank",           "UK", "brand-store"),
    "https://www.goral-shoes.co.uk":     ("Goral Shoes",           "UK", "brand-store"),
    "https://www.thisthingofours.co.uk": ("This Thing Of Ours",    "UK", "edit-shop"),
    "https://www.colebuxton.com":        ("Cole Buxton",           "UK", "brand-store"),
    "https://www.thetrilogytapes.com":   ("The Trilogy Tapes",     "UK", "brand-store"),
    "https://www.mkistore.co.uk":        ("MKI MIYUKI ZOKU",       "UK", "brand-store"),
    "https://www.sevenstore.com":        ("SEVENSTORE",            "UK", "edit-shop"),
    "https://www.maharishistore.com":    ("Maharishi",             "UK", "brand-store"),
    "https://shop.palaceskateboards.com":("PALACE SKATEBOARDS",    "UK", "brand-store"),
    "https://www.houseoferrors.org":     ("HOUSE OF ERRORS",       "UK", "brand-store"),
    "https://www.picante.shop":          ("PICANTE",               "UK", "edit-shop"),

    # ── 홍콩 ────────────────────────────────────────────────────────
    "https://www.treeandbranch.com":     ("Tree and Branch",       "HK", "edit-shop"),
    "https://www.vinavast.co":           ("VINAVAST",              "HK", "edit-shop"),
    "https://www.karmuelyoung.com":      ("KARMUEL YOUNG",         "HK", "brand-store"),

    # ── 이탈리아 ────────────────────────────────────────────────────
    "https://www.slamjam.com":           ("Slam Jam",              "IT", "edit-shop"),
    "https://www.roa-hiking.com":        ("ROA",                   "IT", "brand-store"),
    "https://www.borderlineofficial.com":("Borderline",            "IT", "brand-store"),
    "https://www.stoneisland.com":       ("Stone Island",          "IT", "brand-store"),

    # ── 스웨덴 ────────────────────────────────────────────────────────
    "https://www.ka-yo.com":             ("KA-YO",                 "SE", "edit-shop"),
    "https://www.axelarigato.com":       ("AXEL ARIGATO",          "SE", "brand-store"),
    "https://www.eytys.com":             ("EYTYS",                 "SE", "brand-store"),
    "https://www.sefr-online.com":       ("Séfr",                  "SE", "brand-store"),

    # ── 스페인 ────────────────────────────────────────────────────────
    "https://www.family3-0.com":         ("Family 3.0",            "ES", "edit-shop"),
    "https://www.velourgarments.eu":     ("Velour Garments",       "ES", "brand-store"),
    "https://www.lindenisenough.com":    ("Linden Is Enough",      "ES", "brand-store"),
    "https://www.camperlab.com":         ("Camperlab",             "ES", "brand-store"),

    # ── 독일 ────────────────────────────────────────────────────────
    "https://www.enfinleve.com":         ("enfin levé",            "DE", "brand-store"),
    "https://www.032c.com":              ("032c",                  "DE", "brand-store"),

    # ── 캐나다 ────────────────────────────────────────────────────────
    "https://www.nomadshop.net":         ("NOMAD",                 "CA", "edit-shop"),
    "https://www.annmsshop.com":         ("ANNMS Shop",            "CA", "edit-shop"),

    # ── 프랑스 ────────────────────────────────────────────────────────
    "https://www.rombaut.com":           ("ROMBAUT",               "FR", "brand-store"),
    "https://apac.coteetciel.com":       ("côte&ciel",             "FR", "brand-store"),

    # ── 덴마크 ────────────────────────────────────────────────────────
    "https://www.aaspectrumstore.com":   ("A.A. Spectrum",         "DK", "brand-store"),
    "https://www.flatlisteyewear.com":   ("FLATLIST EYEWEAR",      "DK", "brand-store"),

    # ── 싱가포르 ──────────────────────────────────────────────────────
    "https://www.aliveform.bio":         ("ALIVEFORM",             "SG", "brand-store"),
    "https://www.limitededt.com":        ("Limited Edt",           "SG", "edit-shop"),

    # ── 네덜란드 ──────────────────────────────────────────────────────
    "https://kr.patta.nl":               ("Patta",                 "NL", "brand-store"),

    # ── 중국 ────────────────────────────────────────────────────────
    "https://www.hamc.us":               ("HAMCUS",                "CN", "brand-store"),

    # ── 대만 ────────────────────────────────────────────────────────
    "https://www.guerrilla-group.co":    ("Guerrilla-Group",       "TW", "edit-shop"),

    # ── 비패션 / 기타 유지 ───────────────────────────────────────────
    "https://www.spigen.co.kr":          ("슈피겐",                 "KR", "non-fashion"),
}


def main() -> None:
    csv_path = Path(__file__).parent.parent / "data" / "channels_cleaned.csv"
    rows: list[dict] = []

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            rows.append(row)

    updated = skipped = 0
    for row in rows:
        url = row["url"]
        if url in MAPPING:
            name, country, ch_type = MAPPING[url]
            row["name"] = name
            row["country"] = country
            # department-store / secondhand-marketplace / non-fashion 은
            # MAPPING 에서도 그대로 명시했으므로 덮어써도 무방
            row["channel_type"] = ch_type
            updated += 1
        else:
            skipped += 1
            print(f"  [SKIP] 매핑 없음: {url}")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ 완료: {updated}개 업데이트, {skipped}개 스킵")
    print(f"   저장 위치: {csv_path}")


if __name__ == "__main__":
    main()
