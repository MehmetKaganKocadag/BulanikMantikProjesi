"""Teknik raporu üretir: report/report.docx ve (Windows'ta Word kuruluysa) report/report.pdf.

Çalıştırma (repo kökünden):  python report/build_report.py

Bütün sayılar results/ altındaki deney çıktılarından ve docs/ altındaki checkpoint belgelerinden alınmıştır.
Kaynaklar IEEE kuralına göre metindeki ilk atıf sırasıyla numaralandırılır ({anahtar} → [n]).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_SECTION  # noqa: E402,F401
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report"
ASSETS = OUT / "assets"
FIG = ROOT / "results" / "figures"

# --------------------------------------------------------------------------- kaynaklar (references/README.md)
REFS = {
    "paper": 'R. Manchanda, S. Panchal, R. Sandiri, G. Sudhamsu, A. Mehta, R. Gupta, A. Bhowmik, and B. B. Bukate, '
             '"Energy-efficient clustering and routing for IoT-enabled healthcare using adaptive fuzzy logic and hybrid '
             'optimization," Sci. Rep., vol. 15, Art. no. 34619, 2025, doi: 10.1038/s41598-025-18243-z.',
    "zadeh": 'L. A. Zadeh, "Fuzzy sets," Inf. Control, vol. 8, no. 3, pp. 338–353, 1965, '
             'doi: 10.1016/S0019-9958(65)90241-X.',
    "mamdani": 'E. H. Mamdani and S. Assilian, "An experiment in linguistic synthesis with a fuzzy logic controller," '
               'Int. J. Man-Mach. Stud., vol. 7, no. 1, pp. 1–13, 1975, doi: 10.1016/S0020-7373(75)80002-2.',
    "takagi": 'T. Takagi and M. Sugeno, "Fuzzy identification of systems and its applications to modeling and control," '
              'IEEE Trans. Syst., Man, Cybern., vol. SMC-15, no. 1, pp. 116–132, 1985, doi: 10.1109/TSMC.1985.6313399.',
    "kennedy": 'J. Kennedy and R. Eberhart, "Particle swarm optimization," in Proc. ICNN\'95 – Int. Conf. Neural Netw., '
               'vol. 4, 1995, pp. 1942–1948, doi: 10.1109/ICNN.1995.488968.',
    "leach00": 'W. R. Heinzelman, A. Chandrakasan, and H. Balakrishnan, "Energy-efficient communication protocol for '
               'wireless microsensor networks," in Proc. 33rd Annu. Hawaii Int. Conf. Syst. Sci., 2000, '
               'doi: 10.1109/HICSS.2000.926982.',
    "leach02": 'W. B. Heinzelman, A. P. Chandrakasan, and H. Balakrishnan, "An application-specific protocol architecture '
               'for wireless microsensor networks," IEEE Trans. Wireless Commun., vol. 1, no. 4, pp. 660–670, 2002, '
               'doi: 10.1109/TWC.2002.804190.',
    "gupta": 'I. Gupta, D. Riordan, and S. Sampalli, "Cluster-head election using fuzzy logic for wireless sensor '
             'networks," in Proc. 3rd Annu. Commun. Netw. Services Res. Conf. (CNSR\'05), 2005, pp. 255–260, '
             'doi: 10.1109/CNSR.2005.27.',
    "dijkstra": 'E. W. Dijkstra, "A note on two problems in connexion with graphs," Numer. Math., vol. 1, no. 1, '
                'pp. 269–271, 1959, doi: 10.1007/BF01386390.',
    "bean": 'J. C. Bean, "Genetic algorithms and random keys for sequencing and optimization," ORSA J. Comput., '
            'vol. 6, no. 2, pp. 154–160, 1994, doi: 10.1287/ijoc.6.2.154.',
    "ruspini": 'E. H. Ruspini, "A new approach to clustering," Inf. Control, vol. 15, no. 1, pp. 22–32, 1969, '
               'doi: 10.1016/S0019-9958(69)90591-9.',
    "wilcoxon": 'F. Wilcoxon, "Individual comparisons by ranking methods," Biometrics Bull., vol. 1, no. 6, pp. 80–83, '
                '1945, doi: 10.2307/3001968.',
    "holm": 'S. Holm, "A simple sequentially rejective multiple test procedure," Scand. J. Statist., vol. 6, no. 2, '
            'pp. 65–70, 1979.',
    "shi": 'Y. Shi and R. Eberhart, "A modified particle swarm optimizer," in Proc. IEEE Int. Conf. Evol. Comput., '
           '1998, pp. 69–73, doi: 10.1109/ICEC.1998.699146.',
    "hu": 'H. Hu, X. Fan, and C. Wang, "Energy efficient clustering and routing protocol based on quantum particle '
          'swarm optimization and fuzzy logic for wireless sensor networks," Sci. Rep., vol. 14, Art. no. 18595, '
          '2024, doi: 10.1038/s41598-024-69360-0.',
    "lei": 'C. Lei, "An energy-aware cluster-based routing in the Internet of things using particle swarm optimization '
           'algorithm and fuzzy clustering," J. Eng. Appl. Sci., vol. 71, Art. no. 135, 2024, '
           'doi: 10.1186/s44147-024-00464-0.',
    "sikarwar23": 'N. Sikarwar and R. S. Tomar, "A hybrid MFCM-PSO approach for tree-based multi-hop routing using '
                  'modified fuzzy C-means in wireless sensor network," IEEE Access, vol. 11, pp. 128745–128761, 2023, '
                  'doi: 10.1109/ACCESS.2023.3331312.',
    "prakash": 'V. Prakash, D. Singh, S. Pandey, S. Singh, and P. K. Singh, "Energy-optimization route and cluster head '
               'selection using M-PSO and GA in wireless sensor networks," Wireless Pers. Commun., vol. 146, no. 9, '
               'pp. 5743–5768, 2024, doi: 10.1007/s11277-024-11096-1.',
    "othmen": 'S. Othmen, R. Khdhir, A. Belghith, K. Hamouid, C. Lhioui, and D. Elmourssi, "Enhancing IoT-enabled '
              'healthcare applications by efficient cluster head and path selection using fuzzy logic and enhanced '
              'particle swarm optimization," Int. J. Commun. Syst., vol. 38, no. 3, Art. no. e6096, 2025, '
              'doi: 10.1002/dac.6096.',
    "sennan": 'S. Sennan, S. Ramasubbareddy, R. K. Dhanaraj, A. Nayyar, and B. Balusamy, "Energy-efficient cluster head '
              'selection in wireless sensor networks-based internet of things (IoT) using fuzzy-based Harris hawks '
              'optimization," Telecommun. Syst., vol. 87, no. 1, pp. 119–135, 2024, doi: 10.1007/s11235-024-01176-9.',
    "tawfeek": 'M. A. Tawfeek, I. Alrashdi, M. Alruwaili, and F. M. Talaat, "A fuzzy multi-objective framework for '
               'energy optimization and reliable routing in wireless sensor networks via particle swarm optimization," '
               'Comput. Mater. Contin., vol. 83, no. 2, pp. 2773–2792, 2025, doi: 10.32604/cmc.2025.061773.',
    "maximus": 'A. Renaldo Maximus and S. Balaji, "Energy-efficient fuzzy logic with barnacle mating optimization-based '
               'clustering and hybrid optimized cross-layer routing in wireless sensor network," Int. J. Commun. Syst., '
               'vol. 38, no. 5, Art. no. e6132, 2025, doi: 10.1002/dac.6132.',
    "verma": 'S. Verma, S. Bhatia, S. Zeadally, and S. Kaur, "Fuzzy-based techniques for clustering in wireless sensor '
             'networks (WSNs): Recent advances, challenges, and future directions," Int. J. Commun. Syst., vol. 36, '
             'no. 16, Art. no. e5583, 2023, doi: 10.1002/dac.5583.',
    "hosseinzadeh": 'M. Hosseinzadeh, A. Haider, S. Ali, M. Mohammadi, A. Mehranzadeh, T. Porntaveetus, and J. Lansky, '
                    '"Enhancing DBSCAN clustering with fuzzy system to improve IoT-based WBAN performance," Sci. Rep., '
                    'vol. 15, Art. no. 28404, 2025, doi: 10.1038/s41598-025-13293-9.',
    "sikarwar24": 'N. Sikarwar and R. S. Tomar, "A new approach for wireless sensor networks based on tree-based routing '
                  'using hybrid fuzzy C-means with genetic algorithm," Eng. Technol. Appl. Sci. Res., vol. 14, no. 3, '
                  'pp. 14141–14147, 2024, doi: 10.48084/etasr.7078.',
    "ahmed": 'S. Ahmed, M. A. Hossain, P. H. J. Chong, and S. K. Ray, "Bio-inspired energy-efficient cluster-based '
             'routing protocol for the IoT in disaster scenarios," Sensors, vol. 24, no. 16, Art. no. 5353, 2024, '
             'doi: 10.3390/s24165353.',
    "yuste": 'A. J. Yuste-Delgado, J. C. Cuevas-Martinez, and A. Trivino-Cabrera, "Statistical normalization for a '
             'guided clustering type-2 fuzzy system for WSN," IEEE Sensors J., vol. 22, no. 6, pp. 6187–6195, 2022, '
             'doi: 10.1109/JSEN.2022.3150066.',
    "sharmin": 'S. Sharmin, I. Ahmedy, and R. Md Noor, "An energy-efficient data aggregation clustering algorithm for '
               'wireless sensor networks using hybrid PSO," Energies, vol. 16, no. 5, Art. no. 2487, 2023, '
               'doi: 10.3390/en16052487.',
    "woraphon": 'G. Woraphonbenjakul, A. Masood, and S. Cho, "A survey on fuzzy logic for cluster head selection in '
                'wireless sensor networks," in Proc. Int. Conf. Inf. Netw. (ICOIN), 2023, pp. 725–727, '
                'doi: 10.1109/ICOIN56518.2023.10049015.',
    "repo": 'M. K. Kocadağ, "BulanikMantikProjesi: Adaptif bulanık mantık ile IoT sağlık ağlarında kümeleme ve '
            'yönlendirme — yeniden gerçekleştirme ve geliştirme," GitHub deposu, 2026. [Çevrimiçi]. Erişim: '
            'https://github.com/MehmetKaganKocadag/BulanikMantikProjesi',
}
ORDER: list[str] = []


def cite(text: str) -> str:
    def rep(m):
        nums = []
        for k in m.group(1).split(","):
            k = k.strip()
            if k not in REFS:
                raise KeyError(k)
            if k not in ORDER:
                ORDER.append(k)
            nums.append(ORDER.index(k) + 1)
        return ", ".join(f"[{n}]" for n in nums)

    return re.sub(r"\{([a-z0-9_, ]+)\}", rep, text)


# --------------------------------------------------------------------------- denklemler
EQS = {
    "inputs": r"$E_r=\frac{E_{\mathrm{kalan}}}{E_{0}},\ \ D_{BS}=\frac{d(i,BS)}{d_{\max}},\ \ N_d=\frac{|\mathcal{N}(i)|}{N},"
              r"\ \ L_s=\frac{\mathrm{ACK}_i}{\mathrm{gönderilen}_i}$",
    "adapt": r"$a=\min_i x_i,\quad c=\max_i x_i,\quad b(t+1)=\lambda\, b(t)+(1-\lambda)\,\mathrm{medyan}_i\, x_i$",
    "rules": r"$s=2g_E+g_D+g_N+g_L,\qquad Z=\mathrm{round}(4s/10)\in\{\mathrm{ÇD},\mathrm{D},\mathrm{O},\mathrm{Y},"
             r"\mathrm{ÇY}\}$",
    "defuzz": r"$\mathrm{CH}_{\mathrm{skor}}=\frac{\sum_k \alpha_k w_k z_k}{\sum_k \alpha_k w_k},\qquad "
              r"\alpha_k=\min_{j}\ \mu_{A_{kj}}(x_j)$",
    "fitness": r"$f=\alpha\frac{E}{E_{\mathrm{ref}}}+\beta\frac{D}{D_{\mathrm{ref}}}+\gamma(1-\bar{L})+\delta(1-PDR),"
               r"\qquad PDR=\prod_{h} p(d_h)$",
    "pso": r"$v\leftarrow w\,v+c_1r_1(p_{\mathrm{best}}-x)+c_2r_2(g_{\mathrm{best}}-x),\qquad x\leftarrow x+v$",
    "radio": r"$E_{TX}(k,d)=E_{\mathrm{elec}}k+\epsilon_{fs}kd^2\ (d<d_0),\qquad E_{RX}(k)=E_{\mathrm{elec}}k,"
             r"\qquad p(d)=\frac{0.98}{1+e^{(d-30)/3}}$",
    "hybrid": r"$(a,b,c)_{\mathrm{hibrit}}=(1-\rho)\,(a,b,c)_{\mathrm{adaptif}}+\rho\,(0,\ 0.5,\ 1),\qquad 0\leq\rho\leq 1$",
}


EQ_DPI, EQ_PT = 300, 11.0


def render_eq(key: str, tex: str) -> tuple[Path, float]:
    """Denklemi PNG'ye çizer; döndürür: (yol, doğal genişlik cm). Bütün denklemler aynı punto ile çizilir."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / f"eq_{key}.png"
    with plt.rc_context({"mathtext.fontset": "stix", "font.family": "STIXGeneral"}):
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, tex, fontsize=EQ_PT)
        fig.savefig(path, dpi=EQ_DPI, bbox_inches="tight", pad_inches=0.02, facecolor="white")
        plt.close(fig)
    from PIL import Image
    w_px = Image.open(path).size[0]
    return path, w_px / EQ_DPI * 2.54


# --------------------------------------------------------------------------- belge yardımcıları
doc = Document()
FIG_N, TAB_N, EQ_N = [0], [0], [0]


def setup():
    s = doc.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    s.top_margin = s.bottom_margin = Cm(2.0)
    s.left_margin = s.right_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = st.paragraph_format
    pf.space_after = Pt(4)
    pf.space_before = Pt(0)
    pf.line_spacing = 1.08
    # sayfa numarası
    p = s.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


def add_runs(p, text: str, size=None, italic=False):
    """**kalın** ve *italik* işaretlemesini destekler."""
    text = cite(text)
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("*"):
            r = p.add_run(part[1:-1])
            r.italic = True
        else:
            r = p.add_run(part)
        if italic:
            r.italic = True
        if size:
            r.font.size = Pt(size)
    return p


def P(text: str, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.alignment = align
    return add_runs(p, text)


def bullets(items: list[str]):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(1)
        add_runs(p, it)


def H(text: str, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8 if level == 1 else 5)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(12 if level == 1 else 10.5)
    if level == 2:
        r.italic = True
    return p


def caption(kind: str, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    counter = FIG_N if kind == "Şekil" else TAB_N
    counter[0] += 1
    r = p.add_run(f"{kind} {counter[0]}. ")
    r.bold = True
    r.font.size = Pt(9)
    add_runs(p, text, size=9)
    return counter[0]


def figure(name: str, text: str, width=16.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / name), width=Cm(width))
    return caption("Şekil", text)


def table(header: list[str], rows: list[list[str]], text: str, widths=None, size=8.5):
    n = caption("Tablo", text)
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(cite(h))
        r.bold = True
        r.font.size = Pt(size)
        shade(c, "E8E8E8")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], v, size=size)
    for i, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.keep_with_next = i < len(t.rows) - 1  # tablo bölünmesin
    if widths:
        for row in t.rows:
            for c, w in zip(row.cells, widths):
                c.width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return n


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def equation(key: str):
    EQ_N[0] += 1
    img, w_cm = render_eq(key, EQS[key])
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    c0, c1 = t.rows[0].cells
    c0.width, c1.width = Cm(15.6), Cm(1.4)
    p = c0.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(img), width=Cm(min(w_cm, 15.2)))
    q = c1.paragraphs[0]
    q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    q.add_run(f"({EQ_N[0]})")
    for c in (c0, c1):
        c.vertical_alignment = 1
    return EQ_N[0]


TR = {"Low": "Düşük", "Medium": "Orta", "High": "Yüksek", "VeryLow": "Çok Düşük", "VeryHigh": "Çok Yüksek"}


def rule_table():
    import pandas as pd
    rb = pd.read_csv(ROOT / "results" / "tables" / "rule_base.csv").set_index("rule")
    cnt = pd.read_csv(ROOT / "results" / "tables" / "rule_consequent_counts.csv")
    rows = []
    for k in (19, 1, 47, 41, 64, 63):
        r = rb.loc[k]
        rows.append([str(k), TR[r.energy], TR[r.distance], TR[r.density], TR[r.link], TR[r.ch_suitability]])
    counts = ", ".join(f"{TR[a]} {b}" for a, b in zip(cnt.ch_suitability, cnt.n_rules))
    table(["Kural", "Enerji", "BS'ye uzaklık", "Yoğunluk", "Bağlantı", "CH uygunluğu"], rows,
          f"81 kuraldan örnekler (tam liste: results/tables/rule_base.csv). Çıkış terimlerine göre kural sayıları: "
          f"{counts}. Enerjisi Düşük olan bir düğüm en fazla Orta çıkabilir.", widths=[1.4, 2.4, 3.0, 2.4, 2.4, 3.0])


# --------------------------------------------------------------------------- içerik
def content():
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("IoT Sağlık Ağlarında Adaptif Bulanık Mantık ile Küme Başı Seçimi ve Hibrit PSO-GA Yönlendirme: "
                  "Yeniden Gerçekleştirme, Eleştirel Değerlendirme ve İki Geliştirme")
    r.bold = True
    r.font.size = Pt(14)
    a = doc.add_paragraph()
    a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    a.add_run("Mehmet Kağan Kocadağ — Öğrenci No: 1306230083\n").font.size = Pt(10.5)
    a.add_run("Bulanık Mantık Dersi Dönem Projesi, 2026–2027 · "
              "Kod ve veriler: github.com/MehmetKaganKocadag/BulanikMantikProjesi").font.size = Pt(9)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run("Özet — ")
    r.bold = True
    add_runs(p, "Bu çalışmada, IoT tabanlı sağlık ağları için adaptif bulanık mantık (AFL) ile küme başı (CH) "
                "seçimi ve hibrit PSO-GA ile yönlendirme öneren referans yöntem {paper} Python'da sıfırdan yeniden "
                "gerçekleştirilmiştir. Makalede tanımlanmayan kural tabanı, çıkış üyelik fonksiyonları, kanal ve "
                "trafik modelleri belgelenmiş varsayımlarla tamamlanmış; yöntem LEACH tabanlı ve statik bulanık "
                "karşılaştırmalarla, 30 tohumlu eşleştirilmiş deneylerde değerlendirilmiştir. Makalenin "
                "parametreleriyle (20 düğüm, 100×100 m, 25 m menzil) seçilen CH'lerin %39'unun baz istasyonuna yolu "
                "yoktur ve PDR 0.59'da kalmaktadır (makale: %92.5). Önerilen yöntemin LEACH'e üstünlüğü yeniden "
                "üretilmiş (PDR ≈ 2 kat), ancak adaptif üyelik fonksiyonlarının statik olanlara üstünlüğü "
                "üretilememiştir. İki katkı geliştirilmiştir: (K1) adaptif ve statik bölümlemeyi birleştiren hibrit "
                "üyelik fonksiyonu ve ağ ömrü deneyi; (K6) yönlendirme ablasyonu ve Dijkstra ile başlatılan PSO-GA. "
                "K1 önceden belirlenen başarı ölçütünü karşılamamıştır; nedeni CH seçiminin skorların sıralamasına "
                "dayanması ve bütün bölümlemelerin monoton olmasıdır. K6'da önerilen yöntem, en iyi rotaya ulaşma "
                "oranını 100 düğümde %67'den %89.5'e çıkarırken hesaplama süresini %24 azaltmıştır.", size=10)
    p = doc.add_paragraph()
    r = p.add_run("Anahtar kelimeler — ")
    r.bold = True
    r.font.size = Pt(10)
    add_runs(p, "bulanık mantık, adaptif üyelik fonksiyonu, kablosuz algılayıcı ağlar, küme başı seçimi, PSO-GA, "
                "yeniden üretilebilirlik.", size=10, italic=True)

    # 1 -----------------------------------------------------------------------
    H("1. Giriş (Introduction)")
    P("Giyilebilir sensörler ve hasta başı cihazlar pille çalışır. Verilerin baz istasyonuna (BS) enerji verimli, "
      "düşük gecikmeli ve güvenilir biçimde iletilmesi gerekir. Kümeleme tabanlı mimarilerde her kümenin bir küme "
      "başı (CH) vardır. CH üyelerden veriyi toplar, birleştirir ve BS'ye iletir {leach00}. CH seçimi kalan enerji, "
      "konum, yoğunluk ve bağlantı kalitesi gibi birbiriyle çelişen ve belirsiz ölçütlere bağlıdır. Bu nedenle "
      "bulanık mantık bu probleme sıkça uygulanmıştır {gupta, verma}.")
    P("Referans makale {paper}, dört girdili adaptif bir bulanık sistemle CH seçimi ve hibrit PSO-GA ile çok "
      "atlamalı yönlendirme önerir. Üç Kaggle sağlık veri setinde PDR %92.5, gecikme 0.10 s ve rakip yöntemlere "
      "göre belirgin iyileşmeler bildirir. Makalenin kodu ve verisi yayımlanmamıştır.")
    P("Bu projenin amaçları şunlardır: (i) yöntemi ve deneylerini sıfırdan yeniden gerçekleştirmek; (ii) makaledeki "
      "eksik ve tutarsız noktaları belgelemek; (iii) adil, istatistiksel olarak sınanmış karşılaştırmalar yapmak; "
      "(iv) bulanık çekirdek (K1) ve yönlendirme (K6) üzerine iki deneysel katkı geliştirmek. Bütün kod, ham "
      "sonuçlar ve ara belgeler GitHub deposunda yayımlanmıştır {repo}.")

    # 2 -----------------------------------------------------------------------
    H("2. İlgili Çalışmalar (Related Work)")
    P("**Bulanık CH seçimi.** Gupta ve arkadaşları {gupta}, Mamdani tipi bir bulanık sistemle CH seçen ilk "
      "çalışmalardandır; bu projenin statik bulanık baseline'ı bu yaklaşıma karşılık gelir. Güncel incelemeler "
      "{verma, woraphon}, alanın odağının enerji verimliliği ve ağ ömrü olduğunu gösterir. Son çalışmalar bulanık "
      "değerlendirmeyi çoğunlukla bir metasezgiselle birleştirir. Bunlara örnek olarak Harris şahinleri {sennan}, "
      "barnacle çiftleşme optimizasyonu {maximus} ve kuantum PSO {hu} verilebilir. Yuste-Delgado ve arkadaşları "
      "{yuste}, tip-2 bulanık CH seçiminde girdilerin normalizasyonunu istatistiksel analize dayandırarak uç "
      "değerlerdeki dalgalanmaların etkisini azaltır. Bu, K1'de ele alınan sorunla doğrudan ilişkilidir. "
      "Hosseinzadeh ve arkadaşları {hosseinzadeh} ise WBAN'larda DBSCAN parametrelerini bir bulanık sistemle "
      "uyarlar.")
    P("**Metasezgisel yönlendirme.** PSO, bulanık kümeleme ile {lei}, bulanık c-ortalamalarla {sikarwar23} ve "
      "geliştirilmiş LEACH ile {sharmin} birleştirilmiştir. Tawfeek ve arkadaşları {tawfeek} çelişen hedefleri "
      "bulanık çok amaçlı bir uygunlukla birleştirip yolları PSO ile optimize eder. GA tabanlı hibritler {sikarwar24, "
      "prakash} ve PSO-GA'yı karşılaştırmaya dahil eden BOA-PSO {ahmed} da önerilmiştir. Ahmed ve arkadaşları, "
      "hibrit protokollerin performansının ağ yapılandırmasına büyük ölçüde bağlı olduğunu vurgular. İncelenen "
      "özetlerin hiçbirinde metasezgisel yönlendirme Dijkstra gibi kesin bir yöntemle karşılaştırılmamaktadır. "
      "K6 bu boşluğu hedefler.")
    P("**Sağlık IoT.** Othmen ve arkadaşları {othmen}, enerji, uzaklık ve gecikme girdili bulanık CH seçimini PSO "
      "ile yol seçimiyle birleştirir; bildirdiği değerler (PDR %91.3, 0.12 s, 60.1 bps, 8.9 J/bit) referans "
      "makalenin değerlerine çok yakındır ve aynı birim sorunlarını taşır. Referans makalenin karşılaştırdığı "
      "bazı yöntemler (ANFIS, GA-PSO) ise hastalık tahmini çalışmalarıdır, yönlendirme protokolü değildir.")

    # 3 -----------------------------------------------------------------------
    H("3. Kuramsal Altyapı (Theoretical Background)")
    P("**Bulanık kümeler ve üyelik fonksiyonları.** Bir bulanık küme, evrendeki her elemana [0, 1] aralığında bir "
      "üyelik derecesi atar {zadeh}. Dilsel değişkenler (ör. enerji: Düşük/Orta/Yüksek) bu kümelerle tanımlanır. "
      "Bu projede her girdi tek bir (a, b, c) üçlüsüyle tanımlanan üç terime sahiptir: Düşük (sol omuz), Orta "
      "(üçgen) ve Yüksek (sağ omuz). Üç üyeliğin toplamı her noktada 1'dir (Ruspini bölümlemesi {ruspini}).")
    P("**Çıkarım ve durulaştırma.** Mamdani çıkarımında {mamdani} her kuralın çıktısı bir bulanık kümedir; "
      "kümeler ateşleme gücünde kırpılır, birleştirilir ve ağırlık merkezi alınır. Takagi–Sugeno çıkarımında "
      "{takagi} kuralların çıktısı sayısal bir değerdir ve sonuç ateşleme güçleriyle ağırlıklı ortalamadır. "
      "Referans makalenin \"centroid\" olarak adlandırdığı Denk. (4), her kuralın çıkış kümesinin ağırlık merkezini "
      "tek bir sayı olarak kullandığı için yapı olarak Sugeno tipi bir ağırlıklı ortalamadır. AND işlemi min "
      "t-normuyla yapılır.")
    P("**Adaptif üyelik fonksiyonları.** Statik bölümleme sabit (0, 0.5, 1) kullanır. Adaptif bölümleme ise her "
      "turda gözlenen dağılımdan türetilir. Bu, dağılım daraldığında terimlerin ayırt ediciliğini korur ama "
      "değerlendirmeyi göreli hale getirir.")
    figure("cp2_control_surface.png", "Statik MF ile bulanık sistemin kontrol yüzeyi (Nd = Ls = 0.5). CH skoru "
           "enerjiyle artar, BS'ye uzaklıkla azalır; yüzey parçalı doğrusal ve monotondur.", width=9.0)
    P("**PSO, GA ve rastgele anahtar kodlaması.** PSO {kennedy} her parçacığın hızını kendi ve sürünün en iyi "
      "konumuna doğru günceller; w atalet ağırlığı {shi} keşif ile sömürü arasındaki dengeyi belirler. GA seçim, "
      "çaprazlama ve mutasyonla çeşitlilik sağlar. Sürekli bir optimizasyon algoritmasını yol gibi ayrık bir yapıya "
      "uygulamak için rastgele anahtar (random-key) kodlaması {bean} kullanılmıştır. Parçacık, düğüm başına bir "
      "öncelik vektörüdür ve açgözlü bir çözümlemeyle yola dönüştürülür.")

    # 4 -----------------------------------------------------------------------
    H("4. Referans Yöntem (Original Method)")
    P("**AFL ile CH seçimi.** Her düğüm için dört normalize girdi hesaplanır: kalan enerji, BS'ye uzaklık, komşu "
      "yoğunluğu ve bağlantı kararlılığı (Denk. 1). Adaptif MF parametreleri her turda Denk. (2) ile güncellenir "
      "(λ = 0.7). Kurallar min-AND ile ateşlenir ve CH skoru Denk. (4) ile durulaştırılır. Her yerel bölgede en "
      "yüksek skorlu düğüm CH olur.")
    equation("inputs")
    equation("adapt")
    P("Makale 81 kuralın tamamını ve çıkış üyelik fonksiyonlarını vermez. Bu projede kurallar Denk. (3) ile "
      "sistematik olarak üretilmiştir. g, terimin \"iyilik\" düzeyidir (0, 1, 2); enerjiye çift ağırlık verilir, "
      "uzaklıkta yön terstir. Sonuçta [0, 1] üzerinde beş çıkış teriminden biri (Çok Düşük … Çok Yüksek) "
      "seçilir.")
    equation("rules")
    rule_table()
    equation("defuzz")
    P("**PSO-GA ile yönlendirme.** Her CH'den BS'ye çok atlamalı yol, enerji, gecikme, bağlantı kararlılığı ve "
      "uçtan uca başarı olasılığını birleştiren normalize uygunluk Denk. (5) ile aranır. PSO güncellemesi Denk. "
      "(6) ile yapılır. Her T iterasyonda turnuva seçimi, iki noktalı çaprazlama ve mutasyon ile sürüye çeşitlilik "
      "katılır (30 parçacık, w = 0.7, c₁ = c₂ = 1.5, hız sınırı ±4).")
    equation("fitness")
    equation("pso")
    P("**Eleştirel değerlendirme.** Makalenin ayrıntılı analizinde 24 tutarsızlık belgelenmiştir. Önemlileri "
      "şunlardır: (i) kural ağırlığı güncellemesinde işaret hatası (maliyet artırılıyor); (ii) enerji modelinde "
      "bit sayısının eksikliği; (iii) throughput'un tabloda 61 bps, şekilde 900 000 bps verilmesi ve enerji "
      "verimliliğinin \"J/bit\" birimiyle \"büyük daha iyi\" raporlanması; (iv) makalenin Tablo 3'ündeki GA operatörlerinin "
      "yol kodlamasıyla uyuşmaması; (v) karşılaştırılan ANFIS ve GA-PSO'nun yönlendirme protokolü olmaması; "
      "(vi) \"5 ve 20 SN\" ifadesinin bir yerde sensör, bir yerde küme sayısı anlamında kullanılması ve şekillerin "
      "veri setlerinde bulunmayan bir \"yaş\" eksenine çizilmesi.")

    # 5 -----------------------------------------------------------------------
    H("5. Yeniden Gerçekleştirme Yöntemi (Reproduction Methodology)")
    P("Bütün bileşenler hazır bir bulanık mantık kütüphanesi kullanılmadan, adaptif güncellemenin tam olarak "
      f"denetlenebilmesi için NumPy ile yazılmıştır. Eksik tanımlar için alınan kararlar Tablo {TAB_N[0] + 1}'de "
      "özetlenmiştir.")
    table(["Bileşen", "Makalede", "Bu çalışmada"], [
        ["Üyelik fonksiyonları", "Üçgen, a = min, c = max", "Sol omuz / üçgen / sağ omuz; saf üçgende en iyi düğümün "
                                                             "\"Yüksek\" üyeliği 0 olurdu"],
        ["Kural tabanı", "81 kural, liste yok", "Denk. (3) ile sistematik üretim; her kural açıklanabilir"],
        ["Durulaştırma", "\"Centroid\" (Denk. 10)", "Ağırlıklı ortalama; karşılaştırma için Mamdani centroid de var"],
        ["CH seçimi", "\"Yerel bölgede en yüksek skor\"", "Açgözlü: adaylar skora göre gezilir, 25 m içinde CH "
                                                           "yoksa CH olur (katı yerel maksimum 18 CH üretiyordu)"],
        ["Yol kodlaması", "Belirsiz, GA ile uyumsuz", "Rastgele anahtar {bean}; PSO ve GA aynı vektörde çalışır"],
        ["Enerji modeli", "Hatalı formül", "Birinci derece radyo modeli {leach02}, Denk. (7)"],
        ["Bağlantı / gecikme", "Tanımsız", "Lojistik başarı olasılığı p(d); 250 kbps iletim + yayılım + 1 ms işlem + "
                                           "kuyruk"],
        ["Veri setleri", "Ağ parametrelerine eşleme yöntemi yok", "Trafik kaynağı: ölçüm belirgin değişirse, "
                                                                  "anormalse ya da 10 turdur gönderilmediyse paket"],
    ], "Makalede eksik bırakılan noktalar için alınan kararlar.", widths=[3.0, 4.2, 9.8])
    equation("radio")
    P("**Doğrulama.** 40 birim testi; Ruspini bölümlemesini, kuralların monotonluğunu, enerji muhasebesinin "
      "korunumunu, yolların döngüsüzlüğünü ve PSO-GA'nın küçük grafiklerde kaba kuvvetle bulunan optimuma "
      "yakınlığını (%97–99) sınamaktadır.")
    figure("cp2_adaptive_vs_static.png", "Dar bir enerji bandında (0.52–0.65) statik ve adaptif bölümleme. Statik MF "
           "düğümlerin hepsini \"Orta\" görür; adaptif MF bandı üç terime yayar.", width=11.0)

    # 6 -----------------------------------------------------------------------
    H("6. Önerilen Genişletmeler (Proposed Extension)")
    P("Katkılar, hipotezleri ve başarı ölçütleri deneylerden önce yazılı olarak sabitlenerek tasarlanmıştır.")
    P("**K1 — Hibrit adaptif MF.** Yeniden gerçekleştirmede adaptif MF statik MF'den %1.5–3.8 kötü çıkmıştır. "
      "Nedeni, 100 turun sonunda enerjilerin 0.91–0.98 gibi dar bir bantta kalması ve adaptif bölümlemenin bu "
      "bandı bütün terim aralığına yaymasıdır: %95 enerjili bir düğüm \"Düşük enerjili\" sayılır. Önerilen hibrit "
      "MF, adaptif üçlüyü statik bölümlemeyle dışbükey olarak birleştirir (Denk. 8). ρ = 0 makalenin yöntemi, "
      "ρ = 1 statik MF'dir; dışbükey birleşim sıralamayı ve Ruspini özelliğini korur. ρ ∈ {0.25, 0.5, 0.75} "
      "test tohumlarından ayrı 10 tohumda seçilmiştir. Adaptasyonun yararı ancak enerji farkları oluştuğunda "
      "görülebileceği için değerlendirme ağ ömrü boyunca, homojen ve heterojen (±%50) başlangıç enerjisiyle "
      "yapılmıştır. Başarı ölçütü: 6 hücrenin en az yarısında PH'nin adaptif ya da statik MF'den anlamlı biçimde "
      "iyi, hiçbirinde ikisinden de kötü olmaması.")
    equation("hybrid")
    P("**K6 — Yönlendirme ablasyonu ve Dijkstra başlatmalı PSO-GA (PD).** Makale GA bileşeninin katkısını ölçmez ve "
      "algoritmayı kesin bir yöntemle karşılaştırmaz. Uygunluk fonksiyonunun dört teriminden üçü toplamsaldır. Bu "
      "yüzden toplamsal yaklaşık maliyetle çalışan Dijkstra {dijkstra} çok iyi bir başlangıç noktasıdır. PD'de "
      "Dijkstra'nın yolu, yol düğümlerine azalan yüksek öncelikler verilerek rastgele anahtara çevrilir ve sürünün "
      "ilk parçacığı yapılır. Geri kalanı makalenin PSO-GA'sıdır. Sonuç hiçbir zaman Dijkstra'nın yolundan kötü "
      "olamaz. Karşılaştırılanlar şunlardır: doğrudan iletim (R0), Dijkstra (R1), yalnız PSO (R2), yalnız GA (R3), "
      "PSO-GA (P) ve PD. Başarı ölçütü: her ağ boyutunda en iyi rotaya ulaşma oranının P'den yüksek, değerlendirme "
      "sayısının düşük ve ağ düzeyinde hiçbir ölçütte anlamlı kötüleşme olmaması.")

    # 7 -----------------------------------------------------------------------
    H("7. Deney Düzeni (Experimental Setup)")
    table(["Grup", "Değer"], [
        ["Ağ (makale Tablo 3)", "100×100 m, BS merkezde, 25 m menzil, 2 J/düğüm (K1: 0.25 J), 512 bayt paket, "
                                "E_elec = 50 nJ/bit, ε_fs = 100 pJ/bit/m², E_DA = 5 nJ/bit"],
        ["Bulanık sistem", "4 girdi × 3 terim, 81 kural, 5 çıkış terimi, min-AND, ağırlıklı ortalama, λ = 0.7"],
        ["PSO-GA", "30 parçacık, 100 iterasyon, w = 0.7, c₁ = c₂ = 1.5, hız ±4, GA her 10 iterasyonda (turnuva 3, "
                   "iki noktalı çaprazlama 0.8, mutasyon 0.1), 20 iterasyon iyileşme yoksa dur"],
        ["Veri setleri", "Healthcare IoT (5000 kayıt), Health Monitoring (150), Patient Temp. & Pulse (156); "
                         "z-skor, medyanla doldurma, |z| > 3 aykırı değer"],
        ["Tekrar ve istatistik", "30 tohum (topoloji, trafik ve enerji yöntemden bağımsız → eşleştirilmiş); "
                                 "ortalama ± %95 GA; Wilcoxon işaretli sıra testi {wilcoxon}, Holm düzeltmesi {holm}"],
        ["Yazılım / donanım", "Python 3.13, NumPy 2.2.5, SciPy 1.15.2, pandas 2.2.3, Matplotlib 3.10.1; "
                              "Intel Core i5-12450H (12 mantıksal çekirdek), 32 GB RAM, Windows 11"],
    ], "Deney parametreleri.", widths=[3.3, 13.7])
    table(["Kod", "CH seçimi", "Yönlendirme", "Rolü"], [
        ["P", "AFL (adaptif MF)", "PSO-GA", "Makalenin yöntemi"],
        ["B2", "Statik bulanık {gupta}", "PSO-GA", "Adaptasyonun etkisi"],
        ["B1 / B0", "LEACH {leach00}", "PSO-GA / doğrudan", "Bulanık seçimin ve yönlendirmenin etkisi"],
        ["PH (K1)", "Hibrit MF", "PSO-GA", "Önerilen"],
        ["R0–R3, PD (K6)", "AFL", "Doğrudan, Dijkstra, PSO, GA, Dijkstra başlatmalı PSO-GA", "Ablasyon / önerilen"],
    ], "Karşılaştırılan yöntemler.", widths=[2.4, 3.6, 6.0, 5.0])
    P("**Deneyler.** E1: ana karşılaştırma (N = 20 ve 50, 100 tur; makale Tablo 4–6). E2: atalet ağırlığı "
      "w ∈ {0.3, 0.5, 0.7, 0.9} (makale Tablo 10). E3: 5 düğüm. E6: \"5/20 = küme başı sayısı\" yorumu (100 "
      "sensör, sabit 5 ya da 20 CH, rastgele ve veriden yerleşim). K1: ağ ömrü (N = 50, son düğüm ölene kadar; 720 "
      "test + 240 ayar koşusu). K6: algoritma düzeyi (N = 20/50/100 × 30 topoloji, 7735 rota; N = 20'de kaba kuvvet "
      "optimumu) ve ağ düzeyi (1080 koşu). Toplam yaklaşık 5600 simülasyon koşusu ve 7735 rota optimizasyonu "
      "yapılmıştır.")

    # 8 -----------------------------------------------------------------------
    H("8. Sonuçlar (Results)")
    H("8.1 Yeniden gerçekleştirme", 2)
    figure("e1_metrics_N20.png", "E1 — N = 20 düğümde dört yöntemin karşılaştırması (30 tohum, ortalama ± %95 GA).")
    table(["Ölçüt (3 veri seti)", "P", "B2", "B1", "B0"], [
        ["PDR (N = 20)", "0.593", "**0.604**", "0.593", "0.284"],
        ["Enerji verimliliği, Mbit/J (N = 20)", "2.65", "**2.75**", "2.41", "1.33"],
        ["BS'ye yolu olmayan CH oranı (N = 20)", "0.39", "0.39", "0.35", "0.82"],
        ["PDR (N = 50)", "0.836", "**0.843**", "0.839", "0.290"],
        ["Enerji verimliliği, Mbit/J (N = 50)", "4.27", "**4.34**", "3.64", "1.45"],
    ], "E1 özet sonuçları. P'nin B0'a göre iyileşmesi PDR'de +%108, EE'de +%80–125 (p < 0.001); B1'e göre PDR farkı "
       "yok, EE'de +%6–24 (data1 ve data3'te anlamlı); B2'ye göre −%1.5–3.8 (çoğu anlamsız).",
       widths=[6.5, 2.4, 2.4, 2.4, 2.4])
    table(["Makalenin iddiası", "Bu çalışmadaki bulgu", "Uyum"], [
        ["PDR ≈ %92 (20 düğüm)", "0.59 (N = 20), 0.84 (N = 50)", "✗ — CH'lerin %39'u bağlantısız"],
        ["Gecikme ≈ 0.10–0.13 s", "57–68 ms (N = 20), 72–92 ms (N = 50)", "≈ aynı mertebe"],
        ["Rakiplere göre PDR +%8–33", "LEACH'e göre +%108; LEACH + PSO-GA ile fark yok", "Kısmen"],
        ["Adaptif MF temel katkı", "Statik MF %1.5–3.8 daha iyi (100 tur)", "✗"],
        ["w = 0.7 en iyi, etkisi belirgin", "Ağ metriklerine etkisi yok (Friedman p > 0.2)", "✗"],
        ["5 düğümde yüksek PDR", "%81 CH bağlantısız, PDR 0.27", "✗"],
    ], "Makaleyle karşılaştırma. Makalenin mutlak değerleri kendi içinde tutarsız olduğundan karşılaştırma eğilim "
       "düzeyindedir.", widths=[5.0, 7.5, 4.5])
    table(["w", "PDR (N = 20)", "Gecikme, ms (N = 20)", "Rota uygunluğu f (N = 50)", "Makale: PDR / gecikme"], [
        ["0.3", "0.592", "62.1", "0.2539", "%88.2 / 0.14 s"],
        ["0.5", "0.592", "62.5", "0.2526", "%90.5 / 0.12 s"],
        ["0.7", "0.593", "62.2", "0.2521", "%92.5 / 0.10 s"],
        ["0.9", "0.593", "62.1", "0.2510", "%91.0 / 0.11 s"],
    ], "E2 — Atalet ağırlığının etkisi (P, 3 veri seti × 30 tohum). Friedman testine göre w'nin PDR, throughput ve "
       "EE'ye etkisi anlamsız (p > 0.2); rota uygunluğunda yalnız N = 50'de anlamlı ama fark %1.1.",
       widths=[1.2, 2.8, 3.4, 4.2, 4.4])
    P("\"5/20 SN\" belirsizliği E6'da test edilmiştir. 100 sensör ve 20 CH ile PDR 0.86'ya, veri kayıtlarından "
      "yerleştirilen data3 ağında 0.91'e çıkmaktadır. Adaptif MF yine statik MF'den iyi değildir. Veriden "
      "yerleşimde data2'de kayıtların %87'sinde ECG = 0 olduğundan ağ tamamen kopmaktadır.")
    figure("e6_placement_example.png", "E6 — Veri kayıtlarının iki sütunu alana ölçeklenerek yerleştirilen 100 sensör "
           "(makale Şekil 3–5'in karşılığı). k-means merkezleri (×) makaledeki gibi noktaların arasına düşer; "
           "bulanık yöntemin CH'leri (●) ise her zaman bir düğümdür.", width=15.0)

    H("8.2 K1 — Hibrit adaptif MF ve ağ ömrü", 2)
    figure("k1_metrics.png", "K1 — Ağ ömrü boyunca toplam teslim, FND ve HND (N = 50, E₀ = 0.25 J, 30 tohum).")
    table(["Karşılaştırma", "Toplam teslim", "FND", "HND", "PDR"], [
        ["PH – P", "−1.4 ile −0.2", "−3.0 ile +0.5", "−1.1 ile −0.4", "−1.0 ile −0.2"],
        ["PH – B2", "−0.1 ile +0.2", "−1.5 ile +2.0", "−0.2 ile +0.7", "+0.1 ile +0.2"],
        ["PH – B1", "+9.3 ile +56.5*", "+37 ile +110*", "+7.9 ile +53*", "+8.2 ile +14*"],
        ["P – B2", "+0.4 ile +1.5 (1 hücre*)", "−0.7 ile +2.7", "+0.5 ile +1.7", "+0.4 ile +1.2 (1 hücre*)"],
    ], "K1 — İyileşme yüzdeleri (6 hücre: 2 enerji senaryosu × 3 veri seti; * Holm sonrası p < 0.05). Ayar "
       "aşamasında ρ'nun hiçbir değeri saf adaptif MF'yi geçmedi; seçilen ρ = 0.75.", widths=[2.6, 3.8, 3.4, 3.4, 3.8])
    figure("k1_lifetime.png", "K1 — Canlı düğüm oranının turlara göre değişimi (30 tohum ortalaması). Üç bulanık "
           "varyantın eğrileri neredeyse üst üste; LEACH'te düğümler erken ölmeye başlar ama birkaç düğüm uzun süre "
           "yaşar.", width=15.0)
    P("Başarı ölçütü **karşılanmamıştır**: PH hiçbir hücrede adaptif ya da statik MF'den anlamlı biçimde iyi "
      "değildir. Buna karşın ağ ömrü boyunca adaptif MF statik MF'nin biraz önüne geçer (toplam teslimde "
      "+%0.4–1.5) ve CH sayısını en kararlı tutan varyanttır (standart sapma %4–14 daha düşük).")

    H("8.3 K6 — Yönlendirme ablasyonu", 2)
    figure("k6_algorithm.png", "K6 — Algoritma düzeyi: en iyi bilinen rotaya ulaşma, ortalama göreli fark ve rota "
           "başına CPU süresi. Üst satır yeni ağ (Ls = 1), alt satır yıpranmış ağ (Ls ~ U(0.7, 1)).")
    table(["Ağ, N", "R1 Dijkstra", "R2 PSO", "R3 GA", "P PSO-GA", "PD (önerilen)"], [
        ["Yeni, 50", "99.3 / 0.3", "81.6 / 22.4", "95.2 / 36.9", "84.6 / 25.1", "**99.7 / 18.8**"],
        ["Yeni, 100", "98.8 / 0.6", "58.4 / 37.9", "89.9 / 88.6", "65.3 / 43.7", "**99.1 / 33.0**"],
        ["Yıpranmış, 50", "84.2 / 0.3", "77.7 / 23.3", "95.5 / 39.4", "83.5 / 25.7", "**95.2 / 20.6**"],
        ["Yıpranmış, 100", "79.5 / 0.7", "59.7 / 40.6", "85.8 / 96.3", "67.3 / 48.5", "**89.5 / 36.9**"],
    ], "K6 — En iyi bilinen rotaya ulaşma oranı (%) / rota başına CPU süresi (ms). N = 20'de bütün yöntemler "
       "%97–100. PD, 1547 rotanın hiçbirinde Dijkstra'dan kötü değil.", widths=[2.9, 2.6, 2.6, 2.6, 2.6, 3.0])
    figure("k6_convergence.png", "K6 — Değerlendirme sayısına göre en iyi bilinen çözümden ortalama fark. PD "
           "Dijkstra'nın çözümünden başlar ve onu iyileştirir; algoritmalar erken durma kuralıyla 650–850 "
           "değerlendirmede durur.", width=15.5)
    P("Ağ düzeyinde PD, P, R1, R2 ve R3 arasında PDR, gecikme ve enerji verimliliği açısından anlamlı fark "
      "yoktur (180 test, Holm). Çok atlamalı yönlendirmenin kendisi ise belirleyicidir: P, doğrudan iletime göre "
      "PDR'yi %89–184 artırır. P, Dijkstra'dan 40 (N = 20) ve 81 kat (N = 50) yavaştır; PD, P'den N = 50'de "
      "%22 hızlıdır. Başarı ölçütü **karşılanmıştır**.")
    table(["Performans ölçütü", "Baseline", "Geliştirilen", "Değişim"], [
        ["K1 — Ağ ömrü boyunca teslim edilen okuma (ort.)", "P: 9020", "PH: 8945", "−0.8% (anlamsız)"],
        ["K1 — FND / HND (tur)", "P: 194.5 / 623.2", "PH: 191.0 / 618.5", "−1.8% / −0.7% (anlamsız)"],
        ["K6 — En iyi rotaya ulaşma (N = 100, yıpranmış)", "P: %67.3", "PD: %89.5", "+22.2 puan"],
        ["K6 — Ortalama fark (N = 100, yıpranmış)", "P: %2.84", "PD: %0.33", "8.6 kat küçük"],
        ["K6 — Rota başına süre (N = 100, yıpranmış)", "P: 48.5 ms", "PD: 36.9 ms", "−24%"],
        ["K6 — Yönlendirme süresi, ağ düzeyi (N = 50)", "P: 278 ms/epoch", "PD: 218 ms/epoch", "−22% (p < 0.05)"],
    ], "Baseline ve geliştirilen yöntemlerin karşılaştırması (yönerge 6.2).", widths=[6.6, 3.3, 3.5, 3.6])

    # 9 -----------------------------------------------------------------------
    H("9. Tartışma (Discussion)")
    P("**Makalenin PDR'si neden yeniden üretilemedi?** Tablo 3'teki parametrelerle (20 düğüm, 100×100 m, 25 m) "
      "bir düğümün beklenen komşu sayısı yaklaşık 3'tür ve ağ çoğunlukla bölünmüştür. Bağlantısız CH'ler BS'ye "
      "uzaktan doğrudan göndermek zorunda kalır ve bu iletimler başarısız olur. 50 düğümde bağlantısız CH oranı "
      "%2'ye iner ve PDR 0.84'e çıkar. Makale bu durumu tartışmamaktadır. E6, makalenin aslında çok daha fazla "
      "düğümle çalışmış olabileceğini düşündürmektedir.")
    P("**Üyelik fonksiyonu seçimi neden bu kadar az etkili?** K1'in olumsuz sonucunun temel nedeni CH seçim "
      "mekanizmasıdır. Seçim yalnızca skorların sıralamasını kullanır. Statik, adaptif ve hibrit bölümlemelerin "
      "üçü de her girdide monotondur: daha yüksek enerji hiçbir zaman daha düşük \"Yüksek\" üyeliği vermez. Tek bir "
      "girdiye uygulanan monoton dönüşüm o girdiye göre sıralamayı değiştirmez; MF seçimi yalnızca girdilerin "
      "göreli ağırlığını kaydırır. Bu nedenle üç bulanık varyant arasındaki fark %1.5'i geçmez, LEACH ile fark ise "
      "%9–56'dır. Kısa koşulardaki bozulma ağın başında, düğümlerin hepsi doluyken ortaya çıkar ve ağ ömrünü az "
      "etkiler. İlk ölümlerden sonra ise adaptif bölümleme gerçek bilgi taşır ve hibrit MF bu bilgiyi zayıflatır.")
    P("**Metasezgisel yönlendirme gerekli mi?** Uygunluk neredeyse toplamsal ve rotalar 2–3 atlamalı olduğundan "
      "Dijkstra yeni ağda %99, yıpranmış ağda %80–97 oranında optimumu bulur ve en kötü durumda ortalama %0.6 "
      "geride kalır. Bu kadar küçük uygunluk farkları ağ metriklerine yansımaz. GA bileşeni PSO'ya katkı sağlar, "
      "ama yalnız GA hibritten de iyidir (bu bütçe ve erken durma kuralıyla). PD, Dijkstra'nın neredeyse optimal "
      "çözümünden başladığı için daha az aramayla daha iyi sonuca ulaşır. Bu ölçekte Dijkstra yeterlidir; "
      "toplamsal olmayan hedefler eklendiğinde PD güvenli bir orta yoldur.")

    # 10 ----------------------------------------------------------------------
    H("10. Sınırlılıklar (Limitations)")
    bullets([
        "Kanal, bağlantı, gecikme ve trafik modelleri makalede tanımlı olmadığından varsayımsaldır; sonuçlar göreli "
        "karşılaştırmalar olarak okunmalıdır.",
        "Makalenin rakip yöntemleri (ANFIS, QPSO, ECPF) kodları olmadığından yeniden gerçekleştirilmemiş, yerine "
        "aynı simülatörde LEACH tabanlı baseline'lar kullanılmıştır.",
        "Simülasyon tek kanallı ve çarpışmasızdır; kontrol paketlerinin enerjisi ihmal edilmiştir.",
        "Erken durma sabrı (20 iterasyon) makalede yoktur; PSO tabanlı yöntemlerin sıralaması bu değere duyarlı "
        "olabilir. K6'da N = 50 ve 100 için referans çözüm kesin optimum değil, uzun bir aramanın sonucudur.",
        "K1 yalnızca N = 50 ve E₀ = 0.25 J ile denenmiştir; ρ değerleri arasındaki farklar gürültü düzeyindedir.",
    ])

    # 11 ----------------------------------------------------------------------
    H("11. Sonuç (Conclusion)")
    P("Referans yöntem sıfırdan yeniden gerçekleştirilmiş, eksik tanımları belgelenmiş ve 30 tohumlu eşleştirilmiş "
      "deneylerle değerlendirilmiştir. Bulanık CH seçimi ve çok atlamalı yönlendirmenin LEACH'e üstünlüğü yeniden "
      "üretilmiştir. Buna karşın makalenin adaptif MF ve atalet ağırlığına ilişkin iddiaları ile mutlak PDR "
      "değerleri bu deney düzeninde desteklenmemiştir. Önerilen hibrit MF başarı ölçütünü karşılamamış, bu "
      "olumsuz sonuç CH seçiminin sıralama tabanlı yapısıyla açıklanmıştır. Dijkstra başlatmalı PSO-GA ise makalenin "
      "PSO-GA'sından hem daha doğru hem daha ucuz bulunmuştur.")
    P("**Gelecek çalışmalar:** girdiler arası göreli ağırlığı doğrudan öğrenen kural ağırlığı optimizasyonu (ör. "
      "SPSA), bağlantı ölçümlerindeki gürültüye karşı tip-2 bulanık CH seçimi {yuste}, daha büyük ağlarda "
      "ölçeklenebilirlik analizi ve toplamsal olmayan uygunluk terimleriyle PD'nin değerlendirilmesi.")

    H("Üretken Yapay Zekâ Kullanım Beyanı (Generative AI Usage Disclosure)")
    P("Referans makale öğrenci tarafından okunmuş ve incelenmiştir. Bu projede Anthropic'in Claude modeli "
      "(Claude Code ortamında) yardımcı araç olarak kullanılmıştır. Kullanım alanları: makale analizinin ve "
      "tutarsızlıkların belgelenmesinde taslaklar; uygulama planı; "
      "bulanık çekirdek, simülatör, yönlendirme ve deney kodlarının ilk sürümleri ve birim testleri; özgün "
      "katkıların tasarımı; literatür taramasında aday çalışmaların bulunması; grafiklerin hazırlanması; "
      "checkpoint belgelerinin, bu raporun ve sunumun taslakları. Bütün kaynaklar Crossref üzerinden DOI ile "
      "doğrulanmış, doğrulanamayan adaylar kullanılmamıştır. Raporlanan bütün sonuçlar depodaki betiklerle "
      "üretilmiştir ve yeniden üretilebilir. Kodun, deneylerin ve metnin doğruluğundan öğrenci sorumludur.")


def references():
    H("Kaynaklar (References)")
    for i, k in enumerate(ORDER, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)
        p.paragraph_format.space_after = Pt(1.5)
        r = p.add_run(f"[{i}]\t{REFS[k]}")
        r.font.size = Pt(8.5)


def to_pdf(docx: Path, pdf: Path) -> bool:
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{docx}'); $d.Fields.Update() | Out-Null; "
          f"$d.SaveAs2('{pdf}', 17); $d.Close($false); $w.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=180)
        return pdf.exists()
    except Exception as e:  # Word yoksa yalnızca .docx üretilir
        print("PDF dönüştürme atlandı:", e)
        return False


def main():
    setup()
    content()
    references()
    unused = sorted(set(REFS) - set(ORDER))
    if unused:
        print("Metinde atıf yapılmayan kaynaklar (kaynakçaya alınmadı):", ", ".join(unused))
    OUT.mkdir(exist_ok=True)
    docx = OUT / "report.docx"
    doc.save(docx)
    print(f"{docx} yazıldı ({FIG_N[0]} şekil, {TAB_N[0]} tablo, {EQ_N[0]} denklem, {len(ORDER)} kaynak)")
    if sys.platform == "win32" and to_pdf(docx, OUT / "report.pdf"):
        print(OUT / "report.pdf", "yazıldı")


if __name__ == "__main__":
    main()
