# Adaptif Bulanık Mantık ile IoT Sağlık Ağlarında Enerji Verimli Kümeleme ve Yönlendirme — Yeniden Gerçekleştirme ve Geliştirme

> Bulanık Mantık Dersi Dönem Projesi (2026–2027)

| | |
|---|---|
| **Durum** | 🟡 Checkpoint 1 — Makale ve problem analizi tamamlandı |
| **Dil / Ortam** | Python 3.13 |

---

## Student Information

| | |
|---|---|
| Ad Soyad | Mehmet Kağan Kocadağ |
| Öğrenci No | _(eklenecek)_ |
| Ders | Bulanık Mantık |
| Dönem | 2026–2027 |

## Original Paper

R. Manchanda, S. Panchal, R. Sandiri, G. Sudhamsu, A. Mehta, R. Gupta, A. Bhowmik ve B. B. Bukate,
"Energy-efficient clustering and routing for IoT-enabled healthcare using adaptive fuzzy logic and hybrid optimization,"
*Scientific Reports*, vol. 15, Art. no. 34619, 2025. doi: [10.1038/s41598-025-18243-z](https://doi.org/10.1038/s41598-025-18243-z)

Makalenin yazarları kod ve veriyi yayımlamamıştır ("upon reasonable request"). Bu repodaki tüm kodlar makaledeki
tanımlardan **sıfırdan** yazılmıştır. Makalede eksik bırakılan noktalar için alınan kararlar
[docs/checkpoint1_makale_analizi.md](docs/checkpoint1_makale_analizi.md) içinde belgelenmiştir.

## Problem Description

IoT tabanlı sağlık izleme sistemlerinde (giyilebilir sensörler, hasta başı cihazlar) sensör düğümleri pille çalışır.
Verinin baz istasyonuna (BS) enerji verimli, düşük gecikmeli ve güvenilir biçimde iletilmesi gerekir. Kümeleme
yaklaşımında her kümenin bir **küme başı (Cluster Head, CH)** vardır: CH, üyelerden veriyi toplar ve BS'ye iletir.
CH seçimi; enerji, konum, yoğunluk ve bağlantı kalitesi gibi birbiriyle çelişen ve belirsiz ölçütlere bağlıdır.
Bulanık mantık bu tür çok ölçütlü ve belirsiz kararlar için uygun bir araçtır.

## Method

Referans makale iki aşamalı bir model önerir:

1. **Adaptif Bulanık Mantık (AFL) ile CH seçimi.** Dört girdi kullanılır: kalan enerji, BS'ye uzaklık, düğüm
   yoğunluğu ve bağlantı kararlılığı. Üçgen üyelik fonksiyonlarının parametreleri her turda ağın o anki
   dağılımına göre güncellenir. AND işlemi min ile yapılır, durulaştırma ağırlıklı ortalama ile yapılır.
2. **Hibrit PSO-GA ile yönlendirme.** CH'den BS'ye giden çok atlamalı yol PSO ile aranır. Her T iterasyonda
   GA operatörleri (turnuva seçimi, çaprazlama, mutasyon) sürüye çeşitlilik katar.

## Fuzzy System Architecture

```
            ┌──────────────── Adaptif MF güncellemesi (her tur: a=min, b=ort., c=max, λ-yumuşatma)
            ▼
 Er  ─┐   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐
 DBS ─┼─▶ │ Bulanıklaştır│─▶ │ Kural tabanı │─▶ │ Durulaştırma      │─▶ CH_score(i)
 Nd  ─┤   │ (üçgen MF)   │   │ (min-AND, wk)│   │ (ağırlıklı ortalama)│
 Ls  ─┘   └──────────────┘   └──────────────┘   └───────────────────┘
                                                          │
                       Yerel en yüksek skor ─▶ CH seçimi ─┴─▶ PSO-GA rota optimizasyonu ─▶ BS
```

_(Kural tabanı ve üyelik fonksiyonu parametreleri Checkpoint 2'de eklenecek.)_

## Dataset

Ayrıntılar için: [data/README.md](data/README.md). Üç Kaggle sağlık veri seti kullanılır (Healthcare IoT Data,
Health Monitoring System, Patient Temperature and Pulse Rate).

## Installation

```bash
git clone https://github.com/MehmetKaganKocadag/BulanikMantikProjesi.git
cd BulanikMantikProjesi
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

## Requirements

Python 3.13 ve [requirements.txt](requirements.txt) içindeki paketler (numpy, pandas, matplotlib, scipy).
Bulanık çıkarım motoru, adaptif MF güncellemesinin tam olarak denetlenebilmesi için hazır bir kütüphane yerine
`src/` altında elle yazılacaktır.

## How to Run

_(Checkpoint 3'te eklenecek.)_

## Reproduction Experiments

_(Checkpoint 3'te eklenecek.)_ Planlanan deneyler:
- 20 düğümlü senaryoda PDR, gecikme, throughput ve enerji verimliliği (makale Tablo 4–6)
- PSO inertia weight duyarlılık analizi (makale Tablo 10)

## Proposed Extension

_(Checkpoint 4'te eklenecek.)_ Aday katkılar [docs/checkpoint1_makale_analizi.md](docs/checkpoint1_makale_analizi.md#8-özgün-katkı-adayları) içinde listelenmiştir.

## Experimental Results

_(Checkpoint 5'te eklenecek.)_

## Limitations

_(Proje ilerledikçe güncellenecek.)_ Referans makalenin bilinen sınırlılıkları ve tutarsızlıkları için:
[Checkpoint 1 analizi, bölüm 7](docs/checkpoint1_makale_analizi.md#7-eleştirel-değerlendirme-tutarsızlıklar-ve-eksikler).

## Repository Structure

```
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── docs/                    Checkpoint raporları ve tasarım notları
├── src/                     Bulanık çıkarım, WSN simülatörü, PSO-GA kaynak kodu
├── data/                    Veri seti açıklamaları (ham veri gitignore'da)
├── experiments/baseline/    Referans yöntemin yeniden gerçekleştirme deneyleri
├── experiments/proposed/    Özgün katkı deneyleri
├── results/figures/         Üretilen grafikler
├── results/tables/          Üretilen sonuç tabloları (CSV)
├── presentation/            presentation.pdf
├── report/                  report.pdf
└── references/README.md     Kaynakça (IEEE)
```

## References

Bkz. [references/README.md](references/README.md).

## Generative AI Usage Disclosure

Bu projede üretken yapay zekâ araçları (Claude) makale analizi taslağının hazırlanmasında ve repo iskeletinin
oluşturulmasında yardımcı olarak kullanılmıştır. Tüm içerik öğrenci tarafından okunup doğrulanmaktadır. Kullanımın
ayrıntıları proje ilerledikçe bu bölüme ve teknik rapora eklenecektir.
