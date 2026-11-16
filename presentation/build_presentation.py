"""Sunumu üretir: presentation/presentation.pptx ve (Windows'ta PowerPoint kuruluysa) presentation.pdf.

Çalıştırma (repo kökünden):  python presentation/build_presentation.py

Her slaytın konuşmacı notları savunma hazırlığı için doldurulmuştur. Sayılar results/ ve docs/ ile aynıdır.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "results" / "figures"
OUT = ROOT / "presentation"

INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
BLUE = RGBColor(0x2A, 0x78, 0xD6)
VIOLET = RGBColor(0x62, 0x50, 0xD6)
LIGHT = RGBColor(0xF1, 0xF0, 0xEC)
LINE = RGBColor(0xD6, 0xD4, 0xCC)
GREEN = RGBColor(0x00, 0x83, 0x00)
RED = RGBColor(0xC0, 0x39, 0x2B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"

prs = Presentation()
prs.slide_width, prs.slide_height = Cm(33.867), Cm(19.05)  # 16:9
W, Hh = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]
N = [0]


def text(slide, x, y, w, h, s, size=16, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Cm(0.1)
    lines = s if isinstance(s, list) else [s]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        add_rich(p, ln, size, bold, color)
    return tb


def add_rich(p, s, size, bold=False, color=INK):
    """**kalın** işaretlemesini destekler."""
    parts = s.split("**")
    for j, part in enumerate(parts):
        if not part:
            continue
        r = p.add_run()
        r.text = part
        r.font.size = Pt(size)
        r.font.name = FONT
        r.font.bold = bold or (j % 2 == 1)
        r.font.color.rgb = color


def bullets(slide, x, y, w, h, items, size=17, gap=6):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        level = 1 if it.startswith("  ") else 0
        it = it.strip()
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.level = level
        bullet = "–  " if level else "•  "
        add_rich(p, bullet + it, size - 2 * level, color=INK if level == 0 else INK2)
    return tb


def slide(title, section=None, notes=""):
    s = prs.slides.add_slide(BLANK)
    N[0] += 1
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Cm(0.35))
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    bar.line.fill.background()
    if section:
        text(s, Cm(1.5), Cm(0.75), Cm(25), Cm(0.8), section.upper(), size=11, bold=True, color=BLUE)
    text(s, Cm(1.5), Cm(1.35), Cm(31), Cm(1.6), title, size=28, bold=True)
    text(s, Cm(1.5), Hh - Cm(1.0), Cm(25), Cm(0.7), "Bulanık Mantık Dönem Projesi · M. K. Kocadağ · 1306230083",
         size=10, color=INK2)
    text(s, W - Cm(3.5), Hh - Cm(1.0), Cm(2.0), Cm(0.7), str(N[0]), size=10, color=INK2, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def picture(s, name, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = w
    if h is not None:
        kw["height"] = h
    return s.shapes.add_picture(str(FIG / name), x, y, **kw)


def box(s, x, y, w, h, label, fill=LIGHT, color=INK, size=14, bold=True, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    b = s.shapes.add_shape(shape, x, y, w, h)
    b.fill.solid()
    b.fill.fore_color.rgb = fill
    b.line.color.rgb = LINE
    tf = b.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, ln in enumerate(label.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        add_rich(p, ln, size if i == 0 else size - 3, bold=bold and i == 0, color=color)
    return b


def arrow(s, x1, y1, x2, y2):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = INK2
    c.line.width = Pt(1.75)
    ln = c.line._get_or_add_ln()
    from pptx.oxml.ns import qn
    from lxml import etree
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    return c


def table(s, x, y, w, rows, col_w, size=13, header_fill=BLUE, row_h=Cm(0.85)):
    shp = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, row_h * len(rows))
    t = shp.table
    for j, cw in enumerate(col_w):
        t.columns[j].width = cw
    for i, row in enumerate(rows):
        t.rows[i].height = row_h
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            c.margin_left = c.margin_right = Cm(0.15)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = c.text_frame.paragraphs[0]
            add_rich(p, v, size, bold=(i == 0), color=WHITE if i == 0 else INK)
            c.fill.solid()
            c.fill.fore_color.rgb = header_fill if i == 0 else (WHITE if i % 2 else LIGHT)
    return t


def callout(s, x, y, w, h, msg, fill=BLUE, size=16):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    b.fill.solid()
    b.fill.fore_color.rgb = fill
    b.line.fill.background()
    tf = b.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Cm(0.4)
    p = tf.paragraphs[0]
    add_rich(p, msg, size, color=WHITE)
    return b


# =========================================================================== slaytlar
def build():
    # 1 — kapak
    s = prs.slides.add_slide(BLANK)
    N[0] += 1
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Hh)
    bg.fill.solid()
    bg.fill.fore_color.rgb = RGBColor(0x14, 0x2B, 0x4A)
    bg.line.fill.background()
    text(s, Cm(2), Cm(4.0), Cm(30), Cm(5), ["IoT Sağlık Ağlarında Adaptif Bulanık Mantık ile",
                                             "Küme Başı Seçimi ve Hibrit PSO-GA Yönlendirme"],
         size=34, bold=True, color=WHITE)
    text(s, Cm(2), Cm(8.6), Cm(30), Cm(1.5), "Yeniden gerçekleştirme, eleştirel değerlendirme ve iki geliştirme",
         size=20, color=RGBColor(0xC9, 0xD8, 0xF0))
    text(s, Cm(2), Cm(12.2), Cm(30), Cm(3), ["Mehmet Kağan Kocadağ · 1306230083",
                                              "Bulanık Mantık Dersi Dönem Projesi · 2026–2027",
                                              "github.com/MehmetKaganKocadag/BulanikMantikProjesi"],
         size=16, color=WHITE)
    s.notes_slide.notes_text_frame.text = (
        "Referans makale: Manchanda ve ark., Scientific Reports 15:34619 (2025). Kodu yayımlanmamış; her şey "
        "makaledeki tanımlardan sıfırdan yazıldı. Sunum akışı: problem → makale → bulanık altyapı → yeniden "
        "gerçekleştirme → sonuçlar → iki katkı → sınırlılıklar → canlı demo.")

    # 2 — problem
    s = slide("Problem ve motivasyon", "Giriş",
              "Ana fikir: CH seçimi çok ölçütlü ve belirsiz bir karar; bulanık mantık bu yüzden uygun. Makale buna "
              "bir de 'ağa göre uyarlanan MF' ekliyor.")
    bullets(s, Cm(1.5), Cm(3.6), Cm(16), Cm(13), [
        "Giyilebilir ve hasta başı sensörler **pille çalışır**",
        "Veri baz istasyonuna (BS) **enerji verimli, düşük gecikmeli, güvenilir** iletilmeli",
        "Kümeleme: her kümenin bir **küme başı (CH)** var",
        "  CH veriyi toplar, birleştirir, BS'ye iletir",
        "CH seçimi çelişen ve belirsiz ölçütlere bağlı",
        "  kalan enerji, BS'ye uzaklık, yoğunluk, bağlantı kalitesi",
        "**Bulanık mantık** bu tür çok ölçütlü kararlar için doğal bir araç",
    ])
    box(s, Cm(19.5), Cm(4.2), Cm(5.5), Cm(2.0), "Sensörler", fill=LIGHT)
    box(s, Cm(19.5), Cm(8.2), Cm(5.5), Cm(2.0), "Küme başı (CH)", fill=RGBColor(0xDC, 0xE8, 0xF8))
    box(s, Cm(19.5), Cm(12.2), Cm(5.5), Cm(2.0), "Baz istasyonu", fill=RGBColor(0xDC, 0xE8, 0xF8))
    arrow(s, Cm(22.25), Cm(6.2), Cm(22.25), Cm(8.2))
    arrow(s, Cm(22.25), Cm(10.2), Cm(22.25), Cm(12.2))
    text(s, Cm(25.6), Cm(6.6), Cm(7), Cm(1.4), "Bulanık CH seçimi", size=14, bold=True, color=BLUE)
    text(s, Cm(25.6), Cm(10.6), Cm(7), Cm(1.4), "PSO-GA çok atlamalı rota", size=14, bold=True, color=BLUE)

    # 3 — referans makale
    s = slide("Referans makale: AFL + PSO-GA", "Referans yöntem",
              "Makale: 4 girdili adaptif bulanık sistem + hibrit PSO-GA. İddialar: PDR %92.5, gecikme 0.10 s, "
              "rakiplere göre büyük iyileşme. Kod ve veri yok; kural tabanı ve çıkış MF'leri verilmemiş.")
    xs = [Cm(1.3), Cm(7.5), Cm(13.7), Cm(19.9), Cm(26.1)]
    labels = ["4 girdi\nEr, DBS, Nd, Ls", "Bulanıklaştırma\nadaptif MF (λ = 0.7)", "81 kural\nmin-AND",
              "Durulaştırma\nağırlıklı ortalama", "CH seçimi\nyerel en yüksek skor"]
    for i, (x, lb) in enumerate(zip(xs, labels)):
        box(s, x, Cm(4.0), Cm(5.4), Cm(2.6), lb, fill=RGBColor(0xDC, 0xE8, 0xF8) if i else LIGHT, size=15)
        if i:
            arrow(s, xs[i - 1] + Cm(5.4), Cm(5.3), x, Cm(5.3))
    box(s, Cm(19.9), Cm(8.0), Cm(11.6), Cm(2.6), "Hibrit PSO-GA yönlendirme\nher T iterasyonda GA: turnuva, "
        "çaprazlama, mutasyon", fill=RGBColor(0xE6, 0xE2, 0xF8), size=15)
    arrow(s, Cm(28.8), Cm(6.6), Cm(28.8), Cm(8.0))
    bullets(s, Cm(1.3), Cm(8.0), Cm(17.5), Cm(9), [
        "Uygunluk: enerji + gecikme + bağlantı + uçtan uca PDR",
        "Deney: 100×100 m, **5 ve 20 düğüm**, 25 m menzil, 2 J",
        "3 Kaggle sağlık veri seti",
        "Bildirilen: **PDR %92.5**, gecikme 0.10 s, EE \"9.1\"",
        "Karşılaştırılan: ANFIS, GA-PSO, QPSO, ECPF",
    ], size=16)

    # 4 — literatür
    s = slide("Güncel literatür (2022–2026)", "İlgili çalışmalar",
              "Bütün kaynaklar Crossref'te DOI ile doğrulandı; doğrulanamayan 3 aday alınmadı. Tam liste: "
              "references/README.md ve docs/literatur_taramasi.md.")
    table(s, Cm(1.5), Cm(3.7), Cm(30.8), [
        ["Eğilim", "Örnekler", "Bu projedeki karşılığı"],
        ["Bulanık değerlendirme + metasezgisel", "Harris şahinleri, barnacle, kuantum PSO (2024–2025)",
         "K6: bileşenler ayrı ayrı ölçüldü"],
        ["PSO / GA hibrit yönlendirme", "MFCM-PSO, HFCM-GA, BOA-PSO (2023–2024)", "K6: Dijkstra ile kıyas"],
        ["Girdi normalizasyonu / uyarlama", "Tip-2 bulanık + istatistiksel normalizasyon (2022)",
         "K1: adaptif MF'nin göreli değerlendirme sorunu"],
        ["Sağlık IoT / WBAN", "Bulanık CH + PSO yol seçimi (2025), bulanık DBSCAN (2025)", "Referans makalenin bağlamı"],
        ["İstatistiksel test", "Okunan özetlerde bildirilmiyor", "30 tohum, Wilcoxon + Holm"],
    ], [Cm(8.3), Cm(12.5), Cm(10.0)], size=13, row_h=Cm(1.3))
    callout(s, Cm(1.5), Cm(12.6), Cm(30.8), Cm(1.6),
            "Boşluk: incelenen çalışmaların hiçbiri metasezgisel yönlendirmeyi kesin bir yöntemle (Dijkstra) "
            "karşılaştırmıyor.", size=15)

    # 5 — bulanık altyapı
    s = slide("Bulanık mantık altyapısı", "Kuramsal altyapı",
              "Omuz MF seçimi: makaledeki saf üçgende c = max seçilince en iyi düğümün 'Yüksek' üyeliği 0 olurdu. "
              "Ruspini: üç üyeliğin toplamı 1 (birim testi var). Denk. 10 'centroid' deniyor ama her kural tek bir "
              "sayı veriyor → Sugeno tipi ağırlıklı ortalama.")
    bullets(s, Cm(1.5), Cm(3.5), Cm(15), Cm(6), [
        "Her girdi: **Düşük / Orta / Yüksek**",
        "  sol omuz, üçgen, sağ omuz; tek bir (a, b, c)",
        "  **Ruspini**: üyeliklerin toplamı her yerde 1",
        "Çıkarım: **min-AND**, 81 kural",
    ], size=16)
    bullets(s, Cm(17.5), Cm(3.5), Cm(15), Cm(6), [
        "Durulaştırma (makale Denk. 10): CH = Σ αₖwₖzₖ / Σ αₖwₖ",
        "  \"centroid\" deniyor ama yapı olarak **Sugeno** tipi ağırlıklı ortalama",
        "  karşılaştırma için Mamdani centroid de uygulandı",
    ], size=16)
    picture(s, "cp2_mf_static.png", Cm(1.2), Cm(9.6), w=Cm(31.4))

    # 6 — adaptif MF
    s = slide("Adaptif üyelik fonksiyonları", "Kuramsal altyapı",
              "a = min, c = max, b = medyan (λ ile yumuşatılmış). Dar dağılımda ayırt ediciliği korur ama "
              "değerlendirmeyi göreli yapar: hepsi iyi olsa da en iyisi 'Yüksek', en kötüsü 'Düşük' görünür.")
    picture(s, "cp2_adaptive_vs_static.png", Cm(1.2), Cm(3.4), w=Cm(17.5))
    bullets(s, Cm(19.5), Cm(3.8), Cm(13), Cm(12), [
        "Her turda gözlenen dağılımdan:",
        "  a = min,  c = max",
        "  b(t+1) = λ·b(t) + (1 − λ)·medyan",
        "**Artı:** enerjiler dar bantta toplanınca terimler hâlâ ayırt edici",
        "**Eksi:** değerlendirme göreli olur",
        "  %95 enerjili düğüm, en düşük o ise \"Düşük\" sayılır",
        "Bu eksi, K1 katkısının çıkış noktası",
    ], size=16)

    # 7 — kural tabanı
    s = slide("Kural tabanı: 81 kural, tek formül", "Yeniden gerçekleştirme",
              "Makale kuralları vermiyor. Elle yazmak keyfi olurdu; formülle üretmek her kuralı açıklanabilir yapıyor. "
              "Enerjiye çift ağırlık: enerjisi Düşük olan düğüm en fazla Orta çıkabilir (testi var).")
    callout(s, Cm(1.5), Cm(3.7), Cm(16.5), Cm(1.6), "s = 2·g_E + g_D + g_N + g_L     Z = round(4s / 10)", size=18)
    bullets(s, Cm(1.5), Cm(5.9), Cm(16.5), Cm(6), [
        "g: terimin iyilik düzeyi (0, 1, 2); uzaklıkta yön ters",
        "Enerjiye **çift ağırlık**: CH en çok enerji harcayan rol",
        "Çıkış: 5 terim (Çok Düşük … Çok Yüksek)",
        "Dağılım: 4 / 17 / 39 / 17 / 4 kural",
    ], size=16)
    table(s, Cm(1.5), Cm(11.4), Cm(16.5), [
        ["E", "D", "N", "L", "→ CH"],
        ["Düşük", "Yüksek", "Düşük", "Düşük", "Çok Düşük"],
        ["Orta", "Orta", "Orta", "Orta", "Orta"],
        ["Yüksek", "Düşük", "Yüksek", "Yüksek", "Çok Yüksek"],
    ], [Cm(3.1), Cm(3.1), Cm(3.1), Cm(3.1), Cm(4.1)], size=13, row_h=Cm(0.9))
    picture(s, "cp2_control_surface.png", Cm(19.0), Cm(3.3), w=Cm(13.5))
    text(s, Cm(19.0), Cm(14.6), Cm(13.5), Cm(1.2), "Kontrol yüzeyi: enerjiyle artan, uzaklıkla azalan, monoton",
         size=13, color=INK2, align=PP_ALIGN.CENTER)

    # 8 — PSO-GA
    s = slide("PSO-GA yönlendirme ve rastgele anahtar kodlaması", "Yeniden gerçekleştirme",
              "Sorun: PSO sürekli, yol ayrık. Çözüm: parçacık = düğüm başına öncelik. Çözümleme: CH'den başla, "
              "menzildeki ziyaret edilmemiş en yüksek öncelikli komşuya git, BS'ye ulaşınca dur. Makalenin Tablo 3 "
              "ile metni arasındaki kodlama çelişkisi böylece çözülüyor.")
    bullets(s, Cm(1.5), Cm(3.6), Cm(15.5), Cm(13), [
        "Makale kodlamayı tanımlamıyor; GA operatörleri yol kodlamasıyla uyumsuz",
        "**Rastgele anahtar**: parçacık = düğüm başına bir öncelik",
        "  çözümleme: en yüksek öncelikli menzildeki komşuya git",
        "  PSO denklemleri ve GA operatörleri aynı vektörde çalışır",
        "Uygunluk (normalize, düşük iyi):",
        "  f = α·E + β·D + γ·(1 − L) + δ·(1 − PDR)",
        "30 parçacık, w = 0.7, c₁ = c₂ = 1.5, GA her 10 iterasyonda",
        "Doğrulama: küçük grafiklerde kaba kuvvet optimumunun **%97–99**'u bulunuyor",
    ], size=16)
    xs = [Cm(18.0), Cm(21.6), Cm(25.2), Cm(28.8)]
    for x, (lab, k) in zip(xs, [("CH", "8.1"), ("düğüm 7", "9.4"), ("düğüm 3", "6.2"), ("BS", "—")]):
        box(s, x, Cm(6.0), Cm(3.0), Cm(2.0), f"{lab}\nöncelik {k}", fill=RGBColor(0xDC, 0xE8, 0xF8), size=13)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(s, a + Cm(3.0), Cm(7.0), b, Cm(7.0))
    text(s, Cm(18.0), Cm(8.6), Cm(14), Cm(2.5), "Örnek: öncelik vektörü açgözlü biçimde bir yola çözülür",
         size=13, color=INK2, align=PP_ALIGN.CENTER)

    # 9 — eleştirel değerlendirme
    s = slide("Makalenin eleştirel değerlendirmesi", "Referans yöntem",
              "CP1'de 24 tutarsızlık (T1–T24). Savunmada en çok sorulabilecekler: birim sorunları, 5/20 belirsizliği, "
              "baseline'ların uygunluğu, işaret hatası.")
    table(s, Cm(1.5), Cm(3.6), Cm(30.8), [
        ["Bulgu", "Ayrıntı"],
        ["Birimler tutarsız", "Throughput tabloda 61 bps, şekilde 900 000 bps; EE \"J/bit\" ama büyük daha iyi"],
        ["İşaret hatası", "Kural ağırlığı güncellemesi maliyeti artırıyor (+η yerine −η olmalı)"],
        ["Enerji modeli", "Bit sayısı yok, E_elec mesafeyle çarpılmış"],
        ["Uygunsuz rakipler", "ANFIS ve GA-PSO hastalık tahmini çalışmaları, yönlendirme protokolü değil"],
        ["\"5 ve 20 SN\"", "Tablo 3'te sensör sayısı, şekillerde yüzlerce noktanın küme sayısı"],
        ["Şekiller", "\"Kalp hızı – yaş\" ekseni; üç veri setinde de yaş sütunu yok"],
        ["Kısaltmalar", "\"CH: CH\", \"BS: BS\", \"sensor SNs(SNs)\" — bul-değiştir artıkları"],
    ], [Cm(7.0), Cm(23.8)], size=14, row_h=Cm(1.15))

    # 10 — yeniden gerçekleştirme kararları
    s = slide("Yeniden gerçekleştirme: eksikler nasıl tamamlandı?", "Yeniden gerçekleştirme",
              "Veri setlerinde konum/enerji yok. Makale 'veri kayıtlarından enerji, yoğunluk... atandı' diyor ama "
              "nasıl olduğunu söylemiyor. Fiziksel olarak anlamlı tek yorum: veri = trafik kaynağı.")
    table(s, Cm(1.5), Cm(3.6), Cm(30.8), [
        ["Bileşen", "Makalede", "Bu çalışmada"],
        ["Topoloji", "Belirsiz", "100×100 m'ye rastgele yerleşim, BS merkezde"],
        ["Veri setleri", "Ağa eşleme yöntemi yok", "Trafik kaynağı: ölçüm değişirse / anormalse / 10 turda bir paket"],
        ["Enerji modeli", "Hatalı formül", "Birinci derece radyo modeli (Heinzelman)"],
        ["Bağlantı, gecikme", "Tanımsız", "Lojistik başarı olasılığı p(d); 250 kbps + yayılım + işlem + kuyruk"],
        ["CH seçimi", "\"Yerel en yüksek skor\"", "Açgözlü: skora göre gez, 25 m içinde CH yoksa CH ol"],
        ["İstatistik", "Tek ortalama", "30 tohum, eşleştirilmiş Wilcoxon, Holm düzeltmesi"],
    ], [Cm(6.0), Cm(8.0), Cm(16.8)], size=14, row_h=Cm(1.2))
    callout(s, Cm(1.5), Cm(13.3), Cm(30.8), Cm(1.5), "Python 3.13 + NumPy, hazır bulanık kütüphane yok · 40 birim "
            "testi · ~5600 simülasyon koşusu", fill=INK2, size=15)

    # 11 — E1
    s = slide("Sonuç 1: makalenin senaryosu (N = 20)", "Sonuçlar",
              "B0 gecikmesinin düşük görünmesi hayatta kalma yanlılığı: sadece BS'ye yakın CH'lerin paketleri "
              "ulaşıyor. Asıl mesaj: bağlantısızlık. 20 düğümde ortalama ~3 komşu.")
    picture(s, "e1_metrics_N20.png", Cm(1.0), Cm(3.2), h=Cm(13.8))
    bullets(s, Cm(22.0), Cm(3.6), Cm(11), Cm(13), [
        "P, LEACH'e göre PDR **≈ 2 kat** (p < 0.001)",
        "LEACH + PSO-GA ile PDR farkı **yok**",
        "  kazanç yönlendirmeden geliyor",
        "Statik bulanık (B2) adaptiften **%1.5–3.8 iyi**",
        "PDR 0.59 (makale %92.5)",
        "  CH'lerin **%39'unun** BS'ye yolu yok",
        "  N = 50'de PDR 0.84",
    ], size=16)

    # 12 — makaleyle karşılaştırma
    s = slide("Makaleyle karşılaştırma", "Sonuçlar",
              "Makalenin mutlak sayıları kendi içinde tutarsız olduğu için kıyas eğilim düzeyinde. Tablo 10 "
              "(inertia weight) farkları üretilemedi: Friedman p > 0.2.")
    table(s, Cm(1.5), Cm(3.6), Cm(30.8), [
        ["Makalenin iddiası", "Bu çalışma", "Uyum"],
        ["PDR ≈ %92 (20 düğüm)", "0.59 (N = 20), 0.84 (N = 50)", "✗ bağlantısızlık"],
        ["Gecikme 0.10–0.13 s", "57–68 ms (N = 20), 72–92 ms (N = 50)", "≈ aynı mertebe"],
        ["Rakiplere göre PDR +%8–33", "LEACH'e göre +%108; LEACH + PSO-GA ile fark yok", "Kısmen"],
        ["Adaptif MF temel katkı", "Statik MF %1.5–3.8 daha iyi (100 tur)", "✗"],
        ["w = 0.7 en iyi, etkisi belirgin", "Ağ metriklerine etkisi yok", "✗"],
        ["5 düğümde yüksek PDR", "%81 CH bağlantısız, PDR 0.27", "✗"],
    ], [Cm(9.5), Cm(14.3), Cm(7.0)], size=15, row_h=Cm(1.25))

    # 13 — E6
    s = slide("\"5 ve 20 SN\" ne demek? İki yorumun testi (E6)", "Sonuçlar",
              "Kullanıcı gözlemi: şekillerde merkezler noktaların arasında → k-means görüntüsü. İki yorumu da "
              "test ettik: 100 sensör + 5/20 CH; rastgele ve veriden yerleşim. data2'de ECG'nin %87'si 0 → düğümler "
              "kenarda, ağ kopuyor.")
    picture(s, "e6_placement_example.png", Cm(1.0), Cm(3.2), h=Cm(13.8))
    bullets(s, Cm(22.5), Cm(3.6), Cm(10.5), Cm(13), [
        "Yorum B: 100 sensör, **5 / 20 CH**",
        "  PDR 0.71–0.91; data3'te **0.91**",
        "Adaptif MF yine üstün değil",
        "k-means de AFL kadar iyi",
        "Veriden yerleşim fiziksel olarak tutarsız",
        "  data2'de ağ **tamamen kopuyor**",
    ], size=16)

    # 14 — K1
    s = slide("Katkı K1: hibrit adaptif MF", "Özgün katkı",
              "ρ ayrı tohumlarda seçildi (100–109), test tohumlarında (0–29) değişmedi. Hipotez ve başarı ölçütü "
              "deneyden önce CP4'te yazıldı. Sonuç olumsuz; yönerge 6.2'ye göre nedeni tartışılıyor.")
    callout(s, Cm(1.5), Cm(3.6), Cm(14.5), Cm(1.8), "(a, b, c) = (1 − ρ)·adaptif + ρ·(0, 0.5, 1)", fill=VIOLET,
            size=17)
    bullets(s, Cm(17.0), Cm(3.5), Cm(15.5), Cm(5.5), [
        "ρ = 0 makale, ρ = 1 statik; ρ ayrı tohumlarda seçildi (0.75)",
        "**Ağ ömrü** boyunca; homojen ve heterojen (±%50) enerji",
    ], size=15)
    bullets(s, Cm(1.5), Cm(5.8), Cm(30.5), Cm(3.5), [
        "Başarı ölçütü **karşılanmadı**: PH hiçbir hücrede adaptif ya da statik MF'den anlamlı biçimde iyi değil",
        "Yan bulgu: ağ ömrü boyunca adaptif MF statiğin **biraz önünde** (+%0.4–1.5) · bulanık > LEACH: +%9–56",
    ], size=15)
    picture(s, "k1_metrics.png", Cm(2.5), Cm(8.9), w=Cm(28.5))

    # 15 — K1 neden
    s = slide("K1 neden işe yaramadı?", "Tartışma",
              "Önemli içgörü: seçim sıralamaya dayanıyor ve bütün bölümlemeler monoton. Monoton dönüşüm sıralamayı "
              "değiştirmez; MF seçimi yalnızca girdiler arası göreli ağırlığı kaydırır. Bu yüzden MF varyantları "
              "arası fark <%1.5, LEACH ile fark %9–56.")
    bullets(s, Cm(1.5), Cm(3.8), Cm(17.5), Cm(13), [
        "CH seçimi yalnızca skorların **sıralamasını** kullanır",
        "Statik, adaptif ve hibrit bölümlemeler her girdide **monoton**",
        "  daha yüksek enerji asla daha düşük \"Yüksek\" üyeliği vermez",
        "Monoton dönüşüm o girdiye göre sıralamayı **değiştirmez**",
        "  MF seçimi yalnızca girdiler arası göreli ağırlığı kaydırır",
        "Kısa koşulardaki bozulma ağın başında, herkes doluyken → etkisi az",
        "İlk ölümlerden sonra adaptif MF bilgi taşır; hibrit onu zayıflatır",
    ], size=16)
    picture(s, "k1_lifetime.png", Cm(19.5), Cm(4.0), w=Cm(13.6))

    # 16 — K6
    s = slide("Katkı K6: Dijkstra başlatmalı PSO-GA (PD)", "Özgün katkı",
              "Uygunluğun 4 teriminden 3'ü toplamsal → Dijkstra neredeyse optimum. PD: Dijkstra'nın yolunu rastgele "
              "anahtara çevir, ilk parçacık yap. Garanti: Dijkstra'dan kötü olamaz (1547 rotada 0 ihlal). Yıpranmış "
              "ağ koşulunu adil olsun diye ekledim (Ls = 1'de Dijkstra kayırılıyordu).")
    bullets(s, Cm(1.5), Cm(3.8), Cm(12.5), Cm(13), [
        "İlk parçacık = **Dijkstra'nın yolu**",
        "  geri kalanı makalenin PSO-GA'sı",
        "  garanti: Dijkstra'dan kötü değil",
        "Ablasyon: doğrudan, Dijkstra, yalnız PSO, yalnız GA",
        "**N = 100**, yıpranmış ağ:",
        "  en iyiye ulaşma %67 → **%89.5**",
        "  süre 48.5 → **36.9 ms** (−%24)",
        "Başarı ölçütü **karşılandı**",
    ], size=16)
    picture(s, "k6_algorithm.png", Cm(14.3), Cm(3.4), w=Cm(19.0))

    # 17 — K6 ağ düzeyi
    s = slide("K6: ağ düzeyinde ne değişiyor?", "Sonuçlar",
              "Ağ düzeyinde optimizasyon algoritması önemsiz: uygunluk farkları %3–4'ün altında ve rotalar 2–3 atlamalı. "
              "Önemli olan çok atlamalı yönlendirme yapmak. Yalnız GA hibritten iyi ama ~2 kat yavaş.")
    picture(s, "k6_network.png", Cm(1.0), Cm(3.4), w=Cm(31.8))
    callout(s, Cm(1.5), Cm(14.2), Cm(30.8), Cm(2.0),
            "PD, P, Dijkstra, PSO ve GA arasında PDR / EE farkı yok (180 test, Holm) · Dijkstra 40–81 kat ucuz · "
            "doğrudan iletime göre PDR +%89–184", size=15)

    # 18 — baseline vs geliştirilen
    s = slide("Baseline ve geliştirilen yöntemler", "Sonuçlar",
              "Yönerge 6.2'deki tablo biçimi. K1 olumsuz, K6 olumlu; ikisi de deneyden önce yazılmış ölçütlere göre "
              "değerlendirildi.")
    table(s, Cm(1.5), Cm(3.8), Cm(30.8), [
        ["Performans ölçütü", "Baseline", "Geliştirilen", "Değişim"],
        ["K1 — ağ ömrü boyunca teslim edilen okuma", "P: 9020", "PH: 8945", "−0.8% (anlamsız)"],
        ["K1 — FND / HND (tur)", "194.5 / 623.2", "191.0 / 618.5", "−1.8% / −0.7% (anlamsız)"],
        ["K6 — en iyi rotaya ulaşma (N = 100)", "P: %67.3", "PD: %89.5", "+22.2 puan"],
        ["K6 — optimumdan ortalama fark", "%2.84", "%0.33", "8.6 kat küçük"],
        ["K6 — rota başına CPU süresi", "48.5 ms", "36.9 ms", "−24%"],
        ["K6 — ağ düzeyi yönlendirme süresi (N = 50)", "278 ms/epoch", "218 ms/epoch", "−22% (p < 0.05)"],
    ], [Cm(12.3), Cm(5.5), Cm(5.5), Cm(7.5)], size=15, row_h=Cm(1.3))

    # 19 — sınırlılıklar
    s = slide("Sınırlılıklar ve gelecek çalışmalar", "Tartışma",
              "Dürüst ol: modeller varsayımsal, rakipler farklı. Gelecek: kural ağırlığı öğrenme (SPSA) doğrudan "
              "girdiler arası ağırlığı hedefler — K1'in bulgusuyla tutarlı sonraki adım.")
    bullets(s, Cm(1.5), Cm(3.8), Cm(15.5), Cm(13), [
        "**Sınırlılıklar**",
        "  kanal, bağlantı, gecikme, trafik modelleri varsayımsal",
        "  ANFIS / QPSO / ECPF yerine LEACH tabanlı baseline'lar",
        "  tek kanal, çarpışma yok, kontrol paketi enerjisi yok",
        "  erken durma (20 iterasyon) bizim varsayımımız",
        "  K1 yalnızca N = 50, E₀ = 0.25 J",
    ], size=16)
    bullets(s, Cm(17.5), Cm(3.8), Cm(15), Cm(13), [
        "**Gelecek çalışmalar**",
        "  kural ağırlığı öğrenme (SPSA): girdiler arası ağırlığı doğrudan hedefler",
        "  gürültülü bağlantı ölçümü için tip-2 bulanık CH seçimi",
        "  daha büyük ağlarda ölçeklenebilirlik",
        "  toplamsal olmayan hedeflerle PD",
    ], size=16)

    # 20 — sonuç
    s = slide("Sonuç", "Sonuç",
              "Demo: python experiments/demo.py — CH skoru hesaplama (ateşlenen kurallarla) ve küçük bir ağda "
              "yöntem karşılaştırması.")
    bullets(s, Cm(1.5), Cm(3.8), Cm(30), Cm(9), [
        "Yöntem **sıfırdan** yeniden gerçekleştirildi; 24 tutarsızlık belgelendi",
        "Bulanık CH seçimi + çok atlamalı yönlendirmenin LEACH'e üstünlüğü **yeniden üretildi**",
        "Adaptif MF, atalet ağırlığı ve mutlak PDR iddiaları **desteklenmedi**",
        "K1 olumsuz ama açıklandı: sıralama tabanlı seçimde MF seçiminin etkisi sınırlı",
        "K6 olumlu: PD makalenin PSO-GA'sından **hem daha doğru hem daha ucuz**",
    ], size=18)
    callout(s, Cm(1.5), Cm(12.6), Cm(30.8), Cm(2.0), "Canlı demo:  python experiments/demo.py", fill=INK, size=18)


def to_pdf(pptx: Path, pdf: Path) -> bool:
    ps = (f"$p = New-Object -ComObject PowerPoint.Application; "
          f"$d = $p.Presentations.Open('{pptx}', $true, $false, $false); "
          f"$d.SaveAs('{pdf}', 32); $d.Close(); $p.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=180)
        return pdf.exists()
    except Exception as e:
        print("PDF dönüştürme atlandı:", e)
        return False


def main():
    build()
    OUT.mkdir(exist_ok=True)
    pptx = OUT / "presentation.pptx"
    prs.save(pptx)
    print(f"{pptx} yazıldı ({N[0]} slayt)")
    if sys.platform == "win32" and to_pdf(pptx, OUT / "presentation.pdf"):
        print(OUT / "presentation.pdf", "yazıldı")


if __name__ == "__main__":
    main()
