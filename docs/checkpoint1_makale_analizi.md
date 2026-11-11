# Checkpoint 1 — Referans Makale ve Problem Analizi

> **Referans makale:** R. Manchanda *et al.*, "Energy-efficient clustering and routing for IoT-enabled healthcare
> using adaptive fuzzy logic and hybrid optimization," *Scientific Reports*, vol. 15, Art. no. 34619, 2025.
> doi: [10.1038/s41598-025-18243-z](https://doi.org/10.1038/s41598-025-18243-z)
> (Alındı: 27.05.2025 · Kabul: 31.08.2025 · Yayın: 03.10.2025 · Lisans: CC BY-NC-ND 4.0)
>
> Bu belgede denklem (Denk.), tablo (Tablo) ve şekil (Şekil) numaraları **makaledeki numaralardır**.

---

## 1. Problem ve motivasyon

- **Uygulama alanı:** IoT tabanlı sağlık izleme. Giyilebilir ve hasta başı sensörler kalp hızı, nabız, tansiyon,
  SpO2 ve sıcaklık gibi verileri sürekli toplar ve kablosuz sensör ağı (WSN) üzerinden baz istasyonuna (BS)
  iletir.
- **Neden önemli:** Uzaktan hasta takibi ve acil müdahale düşük gecikme ve yüksek güvenilirlik ister. Paket
  kaybı, kritik bir hasta verisinin kaybı demektir. Sensörler pille çalıştığı için enerji de sınırlıdır.
- **Mevcut yöntemlerin sınırlılığı (makaleye göre):**
  - Klasik kümeleme ve yönlendirme protokolleri ağ koşullarına dinamik olarak uyum sağlamaz. Bu da düğümlerin
    erken tükenmesine ve yüksek gecikmeye yol açar.
  - Hibrit yöntemler (FCM+PSO+GA, QPSO+fuzzy, PSO+derin öğrenme) iyi sonuç verir ancak hesaplama yükleri
    yüksektir.
- **Neden bulanık mantık:** CH seçimi birbiriyle çelişen ve belirsiz ölçütlere bağlıdır. Örneğin bir düğüm
  "enerjisi yüksek ama BS'ye uzak" olabilir. Bulanık çıkarım bu ölçütleri dilsel kurallarla ve keskin eşikler
  kullanmadan birleştirir. Hesaplama maliyeti de düşüktür.

## 2. Amaç ve katkı iddiaları

Makalenin kendi ifadesiyle dört katkısı vardır:

1. Kalan enerji, düğüm yoğunluğu, BS'ye uzaklık ve bağlantı kararlılığını kullanan **adaptif bulanık mantık
   (AFL) tabanlı dinamik CH seçimi.**
2. **PSO ve GA'yı birleştiren hibrit yönlendirme.** PSO hızlı yakınsama, GA ise global arama sağlar.
3. MATLAB ve Google Colab'da, üç Kaggle sağlık veri setiyle yapılan simülasyonlar.
4. ANFIS, GA-PSO, QPSO ve ECPF'ye göre üstün performans iddiası: PDR %92.5, gecikme 0.10 s, throughput
   61.5 bps, enerji verimliliği 9.1.

## 3. Yöntem

### 3.1 Sistem mimarisi (Şekil 2, Algoritma 1)

```
Veri seti → [Aşama 1] AFL ile CH seçimi → Küme oluşumu → [Aşama 2] PSO-GA rota optimizasyonu
          → Veri toplama ve iletim → (CH enerjisi eşik altına düşerse) yeniden kümeleme
```

### 3.2 Bulanık sistemin girdileri (Denk. 2–5)

| Girdi | Tanım | Aralık | "İyi" yön |
|---|---|---|---|
| Kalan enerji $E_r(i)$ | $E_{curr}(i)/E_{init}(i)$ | [0,1] | Yüksek |
| BS'ye uzaklık $D_{BS}(i)$ | $d(i,BS)/d_{max}$ | [0,1] | Düşük |
| Düğüm yoğunluğu $N_d(i)$ | $N_{neighbors}(i)/N_{total}$ (iletişim yarıçapı içindeki komşular) | [0,1] | Yüksek |
| Bağlantı kararlılığı $L_s(i)$ | $P_{recv}(i)/P_{sent}(i)$ | [0,1] | Yüksek |

**Çıktı:** CH uygunluk skoru $CH_{score}(i)$. Çıktının dilsel terimleri ve üyelik fonksiyonları makalede
**verilmemiştir.**

> Not: Özette dördüncü girdi olarak "mobility" sayılır, ancak yöntem bölümünde mobilite yerine "BS'ye uzaklık"
> kullanılır.

### 3.3 Bulanıklaştırma ve adaptif üyelik fonksiyonları (Denk. 1, 6, 7)

- **MF tipi:** Üçgen MF (Denk. 6). Dilsel terimler Düşük / Orta / Yüksek.

  ```math
  \mu(x;a,b,c)=\max\left(\min\left(\frac{x-a}{b-a},\frac{c-x}{c-b}\right),0\right)
  ```

- **Adaptasyon kuralı:** Her turun başında o anki düğüm değerlerinin dağılımına göre güncellenir:
  - $a \leftarrow \min_i x_i$
  - $c \leftarrow \max_i x_i$
  - $b \leftarrow$ ortalama ya da medyan
- **Yumuşatma:** Salınımı önlemek için merkez yumuşatılır (Denk. 1):
  $b^{(t+1)} = \lambda b^{(t)} + (1-\lambda) b^{new}$
- **Çelişki:** Denk. 7'de ise MF parametrelerinin "optimizasyon algoritmalarıyla" bir maliyet fonksiyonunu
  minimize ederek güncellendiği söylenir:
  $J=\alpha E_{total}+\beta\, Delay+\gamma(1-PDR)$.
  Hangi mekanizmanın gerçekten kullanıldığı belirsizdir.

### 3.4 Kural tabanı (Denk. 8)

- **Genel kural biçimi:**
  `IF Er is A AND DBS is B AND Nd is C AND Ls is D THEN CH suitability is Z`
- **Kural ağırlıkları:** $w_k$ ile ağırlıklandırılır ve şu formülle güncellenir:
  $w_k^{(t+1)} = w_k^{(t)} + \eta\,\partial J/\partial w_k$
- **Eksik bilgi:** Kural sayısı, kuralların kendisi ve η değeri verilmemiştir.

### 3.5 Çıkarım ve durulaştırma (Denk. 9–10)

- **Ateşleme gücü (min-AND):**
  $\alpha_k = \min[\mu_{E_r},\mu_{D_{BS}},\mu_{N_d},\mu_{L_s}]$
- **Durulaştırma:**
  $CH_{score}=\dfrac{\sum_k \alpha_k z_k w_k}{\sum_k \alpha_k w_k}$
  Burada $z_k$, k. kuralın çıktı kümesinin ağırlık merkezidir.

Makale bu yönteme "centroid method" der. Yapı olarak ise **ağırlıklı ortalama (height / Sugeno-tipi)
durulaştırmadır.** Yani çıktı kümelerinin birleşimi üzerinden gerçek bir Mamdani centroid'i hesaplanmaz.

### 3.6 CH seçimi ve küme oluşumu

- Yerel bölgesinde $CH_{score}$ değeri en yüksek olan düğüm CH olur.
- CH olmayan düğümler, iletişim menzilindeki CH'ler arasından "bağlantı kalitesi en iyi" olana katılır
  (Algoritma 1, satır 15–19).
- Bir CH'nin enerjisi eşik altına düşünce yeniden kümeleme tetiklenir (satır 49–54).

### 3.7 Hibrit PSO-GA yönlendirme (Denk. 11–22)

- **Parçacık:** CH'den BS'ye giden bir yol: $X_i=[CH\to N_1\to\dots\to N_k\to BS]$ (Denk. 12).
- **Uygunluk (minimize edilir)** (Denk. 11/14):

  ```math
  f(X)=\alpha E(X)+\beta D(X)+\gamma(1-L(X))+\delta(1-PDR(X)),\quad \alpha+\beta+\gamma+\delta=1
  ```

  | Bileşen | Tanım | Denk. |
  |---|---|---|
  | $E(X)$ | Atlama enerjilerinin toplamı; tek atlama $E_{transmit}=E_{elec}\,d+\epsilon_{amp}\,d^n$ | 15–16 |
  | $D(X)$ | Atlama gecikmelerinin toplamı | 17 |
  | $L(X)$ | Bağlantı kararlılıklarının ortalaması | 18 |
  | $PDR(X)$ | Atlama başarı oranlarının **çarpımı** | 19 |

- **PSO güncellemesi:** Standart sürekli PSO (Denk. 20–21):
  - $V\leftarrow wV+c_1r_1(P_{best}-X)+c_2r_2(G_{best}-X)$
  - $X\leftarrow X+V$
- **GA aşaması (her T iterasyonda):**
  - Turnuva seçimi
  - Yol tabanlı çaprazlama: ortak noktadan alt yolların değişimi
  - Mutasyon: bir ara düğümün menzildeki başka bir komşuyla değiştirilmesi
  - En kötü parçacıkların yavrularla değiştirilmesi (elitizm)
- **Durdurma koşulu:** Maksimum iterasyona ulaşılması, fitness eşiğinin aşılması ya da $G_{best}$'in
  iyileşmemesi. Sonuç: $X_{opt}=G_{best}$ (Denk. 22).

### 3.8 Hesaplama karmaşıklığı (makalenin niteliksel tahmini)

| Bileşen | Karmaşıklık | Değişkenler |
|---|---|---|
| AFL | O(n·r) | n düğüm, r kural |
| PSO | O(p·k·I) | p parçacık, k atlama, I iterasyon |
| GA | O(g log g) / çağrı | g popülasyon |

## 4. Deney düzeni

### 4.1 Simülasyon parametreleri (Tablo 3)

| Parametre | Değer | Parametre | Değer |
|---|---|---|---|
| Alan | 100 × 100 m² | Paket boyutu | 512 byte |
| Düğüm sayısı | 5 ve 20 | $E_{elec}$ | 50 nJ/bit |
| BS konumu | Alanın merkezi | $\epsilon_{amp}$ | 100 pJ/bit/m² |
| Başlangıç enerjisi | 2 J | Veri birleştirme | 5 nJ/bit/sinyal |
| İletişim menzili | 25 m | Kanal | Serbest uzay + çok yollu |
| İterasyon | 100 | | |
| **PSO** | 30 parçacık, w=0.7, c1=c2=1.5, hız [−4, 4] | **GA** | Pop. 30, pc=0.8, pm=0.1, turnuva, iki noktalı çaprazlama, bit-flip mutasyon |

**Ortam:** MATLAB + Google Colab.

**Varsayımlar (makalenin kendi listesi):**
- İdeal kanal
- Homojen düğümler
- Sabit BS
- Mobilite ve düğüm arızası yok

### 4.2 Veri setleri

Üç Kaggle seti kullanılmıştır:
- **data1** — Healthcare IoT Data
- **data2** — Health Monitoring System
- **data3** — Patient Temperature and Pulse Rate

Ön işleme: medyan doldurma, z-skor ile aykırı değer temizliği, ölçekleme, zaman hizalama.

Makaleye göre veri kayıtları "sanal sensör düğümlerine eşlenmiş" ve enerji, yoğunluk, bağlantı kararlılığı ile
yakınlık değerlerini atamakta kullanılmıştır. **Eşlemenin nasıl yapıldığı açıklanmamıştır.**

### 4.3 Performans ölçütleri (Denk. 23–29)

| Ölçüt | Tanım | Denk. |
|---|---|---|
| PDR | $P_{received}/P_{sent}$; yol için atlama oranlarının çarpımı | 23–25 |
| Ortalama gecikme | Atlama gecikmelerinin **ortalaması** ($\frac{1}{k+1}\sum T$) | 26 (Denk. 17'deki toplam tanımla çelişir) |
| Throughput | $P_{received}\cdot S_{packet}/T_{total}$ (bps) | 27 |
| Enerji verimliliği | Başarıyla alınan bit / harcanan enerji (bit/J) | 28–29 (tablolarda birim "J/bit" yazılmış) |

## 5. Makalenin sonuçları

### 5.1 20 düğüm karşılaştırması (Tablo 4–6)

| Veri seti | Ölçüt | ANFIS | GA-PSO | QPSO | ECPF | **Önerilen** |
|---|---|---|---|---|---|---|
| data1 | PDR (%) | 69.5 | 75.8 | 80.1 | 83.2 | **92.1** |
| | Gecikme (s) | 0.36 | 0.31 | 0.27 | 0.24 | **0.11** |
| | Throughput (bps) | 54.0 | 55.4 | 57.0 | 57.6 | **61.2** |
| | EE | 6.4 | 7.2 | 8.0 | 8.3 | **9.0** |
| data2 | PDR (%) | 68.8 | 74.3 | 79.5 | 82.7 | **91.7** |
| | Gecikme (s) | 0.37 | 0.33 | 0.29 | 0.26 | **0.13** |
| | Throughput (bps) | 53.5 | 54.7 | 56.6 | 57.1 | **60.8** |
| | EE | 6.3 | 7.1 | 7.9 | 8.2 | **8.8** |
| data3 | PDR (%) | 70.9 | 77.4 | 82.6 | 85.4 | **92.5** |
| | Gecikme (s) | 0.34 | 0.30 | 0.28 | 0.25 | **0.10** |
| | Throughput (bps) | 54.7 | 56.0 | 58.1 | 58.6 | **61.5** |
| | EE | 6.6 | 7.4 | 8.2 | 8.5 | **9.1** |

### 5.2 Diğer sonuçlar

- **Inertia weight duyarlılığı (Tablo 10):**

  | w | PDR | Gecikme | EE |
  |---|---|---|---|
  | 0.3 | 88.2 | 0.14 | 8.2 |
  | 0.5 | 90.5 | 0.12 | 8.9 |
  | **0.7** | **92.5** | **0.10** | **9.1** |
  | 0.9 | 91.0 | 0.11 | 8.7 |

  En iyi değer w = 0.7. Bu satırdaki sayılar data3 sonuçlarıyla birebir aynıdır, fakat tabloda hangi veri
  setinin kullanıldığı belirtilmemiştir.
- **Paired t-testi (Tablo 11):** Tüm karşılaştırmalarda p < 0.001, t değerleri 3.67 ile 6.45 arasında.
  Örneklem büyüklüğü ve eşleştirme biçimi belirtilmemiştir.
- **Zaman serisi şekilleri (Şekil 12–23):** 100 iterasyon boyunca yaklaşık değerler:

  | Ölçüt | Şekillerdeki aralık |
  |---|---|
  | PDR | ≈ 0.88–0.94 |
  | Gecikme | ≈ 100–145 ms |
  | Throughput | ≈ 820 000–980 000 bps |
  | EE | ≈ 0.58–0.62 |

### 5.3 Sayısal doğrulama (bu proje kapsamında yapıldı)

Tablo 7–9'daki yüzde iyileşmeler Tablo 4–6'daki değerlerden yeniden hesaplandı. 48 değerden 47'si tutarlı
çıktı. Tek tutarsızlık: Tablo 8'de data2 için ANFIS'e göre throughput iyileşmesi **%13.83** yazılmış, doğru
değer (60.8−53.5)/53.5 = **%13.64**.

## 6. Teorik altyapı haritası (sunum ve rapor bölüm 3 için)

| Kavram | Makaledeki karşılığı | Raporda anlatılacak |
|---|---|---|
| Bulanık küme, üyelik fonksiyonu | Üçgen MF (Denk. 6) | Zadeh 1965 tanımı; üçgen, yamuk ve Gauss MF karşılaştırması |
| Dilsel değişken | Er, DBS, Nd, Ls → {Düşük, Orta, Yüksek} | Terim kümesi, evrensel küme |
| Bulanıklaştırma | Normalize girdi → μ değerleri | |
| Kural tabanı | IF–AND–THEN, ağırlıklı kurallar | Kural patlaması: 3⁴ = 81 kural |
| Çıkarım (t-norm) | min-AND (Denk. 9) | min ve çarpım t-normları |
| Durulaştırma | Ağırlıklı ortalama (Denk. 10) | Centroid, bisector, MOM, ağırlıklı ortalama |
| Mamdani ve Sugeno | Makalede belirsiz | İki çıkarım tipinin farkı; Denk. 10'un hangisine denk düştüğü |
| Adaptif FIS / Neuro-fuzzy | MF ve kural ağırlığı güncellemesi | ANFIS ile ilişki ve farklar |
| Metasezgisel optimizasyon | PSO, GA | Kennedy & Eberhart 1995; GA operatörleri |

## 7. Eleştirel değerlendirme: tutarsızlıklar ve eksikler

### 7.1 Güçlü yönler

- Problem gerçek ve önemli: enerji kısıtlı sağlık WSN'leri.
- İki aşamalı tasarım (bulanık CH seçimi + metasezgisel yönlendirme) anlaşılır ve modüler.
- Adaptif MF fikri basit ve hesaplama açısından ucuz. Düğüm değerlerinin dağılımı zamanla değiştiği için
  mantıklı bir gerekçesi var.
- Duyarlılık analizi, istatistiksel test ve sınırlılıklar bölümü gibi iyi uygulama adımları yer alıyor.

### 7.2 Eksik bilgiler (yeniden gerçekleştirmeyi doğrudan etkiler)

| # | Eksik | Konum | Etkisi |
|---|---|---|---|
| E1 | Kod ve veri yayımlanmamış ("upon request") | s. 29 | Her şey sıfırdan yazılmalı |
| E2 | Kural tablosu, kural sayısı, çıktı MF'leri ve $z_k$ değerleri yok | Denk. 8–10 | Kural tabanını kendimiz tasarlamalıyız |
| E3 | λ, η, α–δ ağırlıkları ve GA çağrı aralığı T verilmemiş | Denk. 1, 7, 8, 11 | Varsayım ve duyarlılık analizi gerekir |
| E4 | Ayrık yolun sürekli PSO'da nasıl kodlandığı yok | Denk. 12, 20–21 | Bir kodlama şeması seçilmeli |
| E5 | Gecikme modeli (bit hızı, işlem ve kuyruk süresi) yok | Denk. 17, 26 | Model varsayılmalı |
| E6 | Bağlantı başarı olasılığı modeli yok | Denk. 5, 18, 19 | Mesafeye bağlı bir model varsayılmalı |
| E7 | Kaggle verisinin ağ parametrelerine eşlenmesi tarif edilmemiş | s. 9 | Eşleme tasarlanmalı |
| E8 | Rakip yöntemlerin nasıl gerçekleştirildiği belirtilmemiş | Tablo 4–6 | Sayılarla birebir karşılaştırma yapılamaz |
| E9 | "Yerel bölge" ve CH sayısı tanımı yok | s. 10 | Seçim kuralı tanımlanmalı |

### 7.3 Teknik hatalar ve tutarsızlıklar

| # | Bulgu | Konum | Açıklama |
|---|---|---|---|
| T1 | **İşaret hatası** | Denk. 8 | J minimize edilmek isteniyor ama güncelleme $+\eta\,\partial J/\partial w$ (gradyan çıkışı). Doğrusu $-\eta$ olmalı. J'nin $w_k$'ye göre analitik türevi de tanımlı değil, çünkü simülasyon çıktısı. |
| T2 | **"Centroid" adlandırması** | Denk. 10 | Formül ağırlıklı ortalama. Sistemin Mamdani mi Sugeno mu olduğu belirsiz. |
| T3 | **İki farklı MF adaptasyonu** | Denk. 1 ve 7 | Biri min/ort./max sezgisi, diğeri J'yi minimize eden optimizasyon. Hangisi kullanıldı? |
| T4 | **Enerji modeli hatalı** | Denk. 16 | $E_{elec}\cdot d+\epsilon_{amp}\cdot d^n$: bit sayısı yok, $E_{elec}$ mesafeyle çarpılmış. Standart birinci derece radyo modeli $E_{TX}(k,d)=E_{elec}k+\epsilon_{fs}kd^2$ (d<d₀), $E_{elec}k+\epsilon_{mp}kd^4$ (d≥d₀). |
| T5 | **Birimler ve büyüklükler tutarsız** | Tablo 4–6 ve Şekil 18–23 | Throughput tabloda ~61 bps, şekilde ~900 000 bps. EE tabloda 9.1 "J/bit", şekilde ~0.6, formülde bit/J. Bu radyo modeliyle gerçekçi EE milyonlarca bit/J mertebesinde olurdu (≈ 1/(E_elec + ε·d²) ≈ 3·10⁶ bit/J, d=50 m için). Hiçbir değer fiziksel olarak tutarlı değil. |
| T6 | **Gecikme iki farklı tanımla verilmiş** | Denk. 17 ve 26 | Biri toplam, diğeri atlama başına ortalama. |
| T7 | **PSO ile GA kodlaması uyuşmuyor** | Tablo 3 ve s. 12–13 | Tablo 3 "two-point crossover, bit-flip mutation" diyor; metin yol tabanlı çaprazlama ve düğüm değiştirme mutasyonu anlatıyor. Bit-flip, yol (düğüm dizisi) kodlamasıyla uyumlu değil. |
| T8 | **Şekiller ağ topolojisini göstermiyor** | Şekil 3–11 | Eksenler "kalp hızı – yaş" ve "tansiyon – yaş". Kümeler ve rotalar fizyolojik veri uzayında çizilmiş, düğümlerin fiziksel konumunda değil. Şekil 3'te yüzlerce "sensor point" ve 5 ya da 20 "cluster center" var. Bu, "5 ve 20 düğüm"ün aslında **5 ve 20 küme merkezi** olabileceğini düşündürüyor. |
| T9 | **5 düğümde bağlantısızlık** | Tablo 3 | 100×100 m alanda 25 m menzille 5 düğümün beklenen komşu sayısı < 1 (≈ 4·π·25²/100² ≈ 0.8). Çok atlamalı yol çoğu zaman var olamaz. Makale bunu tartışmıyor. |
| T10 | **$\epsilon_{amp}$ ve kanal tipi** | Tablo 3 | 100 pJ/bit/m², LEACH'teki yaygın 10 pJ/bit/m² değerinin 10 katı. ε_mp verilmemiş. Yaygın ε_mp = 0.0013 pJ/bit/m⁴ ile d₀ = √(100/0.0013) ≈ 277 m çıkar. BS merkezdeyken en uzak mesafe ≈ 70.7 m olduğundan "multipath" modu hiç devreye girmez. |
| T11 | **Abartılı genelleme** | Özet, Sonuç | "Tüm senaryolarda PDR %30'dan fazla, gecikme %60'tan fazla iyileşti" deniyor. PDR iyileşmesi ECPF'ye göre yalnızca %8–11; gecikme iyileşmesi data1 ve data2'de ECPF'ye göre %54 ve %50. Özetteki başlık sayıları üç veri setinin en iyisi olan data3'e ait. |
| T12 | **Karşılaştırılan yöntemlerin uygunluğu** | Tablo 1, 4–6 | ANFIS [31] akciğer kanseri tahmini, GA-PSO [32] kalp hastalığı tahmini çalışmaları. Bunlar routing protokolü değil. Routing problemine nasıl uyarlandıkları belirsiz. |
| T13 | **Kaynak numaraları kaymış** | s. 3, 6, 9, 15 | Tablo 1'de "SI in IoMT²⁷" yazıyor ama [27] Sikarwar, doğrusu [28]. Veri setleri metinde 37–39 diye anılıyor ama URL'ler [38]–[40]'ta. AFL formülasyonu [40]'a atıf yapıyor, [40] ise bir veri seti. |
| T14 | **Konuyla ilgisiz atıflar** | s. 13, Tablo 3 | GA operatörleri ve simülasyon parametreleri için verilen [42]–[45] numaralı kaynaklar lantan katkılı ferrit, L-ornitin/BSA, EDM dielektrik sıvıları ve GRU-LSTM saldırı tespiti üzerine. [44]'ün yazarlarından biri makalenin de yazarı. |
| T15 | **Tablo ve denklem atıf hataları** | s. 12, 26 | "Fitness Eq. (13)" deniyor, doğrusu Denk. 11/14. "Table 4 and Table 6 ... improved percentage" deniyor, doğrusu Tablo 7. |
| T16 | **Bağlantı kararlılığı tanımı** | Denk. 5 | "SN i'nin aldığı paket / SN i'nin gönderdiği paket" düğümün kendi iletim başarısını ölçmez. ACK tabanlı başarı oranı olarak yorumlanmalı. |
| T17 | **Ağ ömrü metrikleri yok** | Bölüm 5 | Enerji verimli WSN çalışmalarında standart olan FND/HND/LND (ilk, yarı ve son düğüm ölümü) raporlanmamış, oysa "ağ ömrü uzatma" iddia ediliyor. |
| T18 | **Veri setleri makaledeki tanımlarla uyuşmuyor** | s. 9 | Kaggle dosyaları indirilip incelendi (ayrıntı: [data/README.md](../data/README.md)). data1'de makalenin saydığı SpO2 ve solunum hızı yok; kayıtların neredeyse hepsi farklı hastalara ait (sürekli izleme serisi değil). data2'de sistolik/diyastolik tansiyon yok; yalnızca 2 hasta, ham "ECG" ve sabite yakın "Pressure" (75–78) sütunları var, sıcaklık 48'e kadar çıkıyor. data3'te hasta kimliği yok; "Pulse" sütunu bpm değil, 0–4095 aralığında 12-bit ham ADC değeri. |

### 7.4 Sınırlılıklar (makalenin kabul ettikleri + bizim eklediklerimiz)

- **Makalenin kabul ettikleri:**
  - İdeal kanal, homojen düğümler, sabit BS
  - Mobilite ve arıza modellenmemiş
  - Hibrit metasezgisel optimizasyonun hesaplama yükü
- **Bizim eklediklerimiz:**
  - Yalnızca 5 ve 20 düğümlü küçük ölçek
  - Mutlak sayıların yeniden üretilemezliği (T5)
  - Belirsiz baseline'lar (T12)
  - Veri setlerinin ağ katmanıyla ilişkisinin zayıf olması (T8) ve içeriklerinin makaledeki tanımlarla
    uyuşmaması (T18)

## 8. Özgün katkı adayları

Yönergenin 6.1 maddesindeki katkı türleriyle eşleştirilmiştir. Checkpoint 4'te biri ya da ikisi seçilecek.

| Aday | Yönerge karşılığı | Gerekçe | Ölçüm |
|---|---|---|---|
| **K1 — Adaptif ve statik MF ablasyonu** | Ablation study | Makalenin ana iddiası ("adaptif MF daha iyi") kontrollü deneyle hiç test edilmemiş | Aynı tohumlarla PDR, EE, FND/HND ve CH sayısı kararlılığı |
| **K2 — Mamdani (gerçek centroid), Sugeno (ağırlıklı ortalama) ve kural ağırlığı öğrenme karşılaştırması** | Mamdani–Sugeno; durulaştırma karşılaştırması | T1 ve T2 belirsizliklerini doğrudan çözer | Skor sıralaması benzerliği (Kendall τ), ağ metrikleri, çalışma süresi |
| K3 — Interval Type-2 bulanık CH seçimi | Type-1–Type-2 | Bağlantı kararlılığı ölçümü gürültülüdür; IT2 belirsizliği MF içinde modeller | Gürültü seviyesine göre PDR ve ömür |
| K4 — Gürültü ve robustluk analizi | Gürültü/robustness | Gerçek ortamda $L_s$ ve enerji tahminleri gürültülüdür | Gürültü σ ∈ {0, 0.05, 0.1, 0.2} için metrik eğrileri |
| K5 — Ölçeklenebilirlik ve ağ ömrü | Yeni deney senaryosu; hesaplama maliyeti | Makale yalnızca 5 ve 20 düğüm denemiş, ömür metriği yok | 20/50/100/200 düğüm; FND/HND/LND; çalışma süresi |
| K6 — PSO, GA ve PSO-GA ablasyonu | Optimizasyon karşılaştırması | GA katkısının gerçekten fark yaratıp yaratmadığı test edilmemiş | Yakınsama eğrileri, en iyi fitness, süre |

**Ön öneri:** K1 + K2 birlikte. İkisi de makalenin bulanık mantık çekirdeğini hedefliyor (ders açısından en
değerli kısım) ve makaledeki belirsizlikleri deneyle cevaplıyor. K4 ve K5 ise düşük maliyetli ek deneyler olarak
eklenebilir.

## 9. Yeniden gerçekleştirme kararları (taslak — Checkpoint 2'de kesinleşecek)

| Konu | Makale | Bu projedeki karar | Gerekçe |
|---|---|---|---|
| Ortam | MATLAB + Colab | Python 3.13 (numpy, scipy, matplotlib) | Açık kaynak, tekrar üretilebilir |
| Bulanık motor | Belirtilmemiş | Elle yazılmış FIS | Adaptif MF ve kural ağırlıkları tam kontrol edilebilir; her adım şeffaf ve test edilebilir |
| Çıktı MF'leri | Yok | 5 terim {Çok Düşük … Çok Yüksek}, [0,1] üzerinde üçgen; $z_k$ = 0, 0.25, 0.5, 0.75, 1 | En yaygın tasarım |
| Kural tabanı | Yok | 3⁴ = 81 kural. Çıktı terimi, girdilerin "iyi yön" seviyelerinin (Düşük=0, Orta=1, Yüksek=2; DBS için ters) toplamından sistematik olarak türetilir | Şeffaf, belgelenebilir, keyfi değil |
| Kural ağırlığı öğrenme | $+\eta\,\partial J/\partial w$ | Temel modelde $w_k=1$. Öğrenme K2 kapsamında, düzeltilmiş işaretle ($-\eta$) ve sonlu farklar ya da SPSA gradyan tahminiyle | T1 düzeltmesi |
| Adaptif MF | min / ort. / max + λ | Denk. 1 uygulanır; λ = 0.7 başlangıç, duyarlılığı raporlanır | E3 |
| Enerji modeli | Hatalı Denk. 16 | Heinzelman birinci derece radyo modeli, Tablo 3 parametreleriyle | T4 düzeltmesi |
| Bağlantı modeli | Yok | Mesafeye bağlı başarı olasılığı (ör. menzil sonuna doğru azalan lojistik eğri), $L_s$ = ACK oranının hareketli ortalaması | E6, T16 |
| Gecikme modeli | Yok | Atlama başına iletim (L/R, R = 250 kbps — IEEE 802.15.4) + yayılma + işlem süresi | E5 |
| Yol kodlaması | Belirsiz | **Rastgele anahtar (priority / random-key) kodlaması:** her parçacık düğüm başına bir öncelik vektörüdür ve açgözlü sonraki-atlama çözümlemesiyle yola dönüştürülür. Böylece Denk. 20–21 değişmeden uygulanabilir; GA çaprazlama ve mutasyonu da bu vektör üzerinde çalışır | E4, T7 |
| Topoloji | Belirsiz (T8) | Düğümler 100×100 m'ye düzgün rastgele yerleştirilir; BS (50, 50) noktasında. Kaggle verisi **trafik kaynağı** olarak kullanılır: her düğüm bir hasta akışını temsil eder, her okuma bir paket üretir | E7 — fiziksel olarak anlamlı tek yorum |
| Bağlantısızlık | Tartışılmamış | Menzil içinde BS'ye yol yoksa CH doğrudan BS'ye iletir (yüksek enerji maliyetiyle) ve bu durum ayrıca raporlanır | T9 |
| Tekrar sayısı | 100 iterasyon | Her yapılandırma için ≥ 30 farklı rastgele tohum; ortalama ± std ve %95 güven aralığı | İstatistiksel geçerlilik |
| Baseline'lar | ANFIS, GA-PSO, QPSO, ECPF | LEACH; statik bulanık CH (Gupta et al. 2005 tarzı); yalnızca PSO; yalnızca GA | Aynı simülatörde adil karşılaştırma (T12) |

### 9.1 Önerilen MRR (Minimum Reproduction Requirement)

> Hoca tarafından ayrıca bir MRR belirlenmişse o geçerlidir. Aşağıdaki öneri onunla karşılaştırılmalıdır.

1. Tur tabanlı WSN simülatörü: düğümler, radyo enerji modeli, bağlantı modeli, ölüm takibi.
2. 4 girdili, adaptif üçgen MF'li, min-AND ve ağırlıklı ortalama durulaştırmalı **bulanık CH seçimi.**
3. Rastgele anahtar kodlamalı, her T iterasyonda GA operatörleri uygulanan **PSO-GA yönlendirme.**
4. PDR, gecikme, throughput, enerji verimliliği ve ek olarak FND/HND.
5. **Tekrar edilecek deneyler:**
   - **D1:** 20 düğüm senaryosu (Tablo 4–6 eğilimi)
   - **D2:** PSO inertia weight duyarlılığı w ∈ {0.3, 0.5, 0.7, 0.9} (Tablo 10)
6. **Karşılaştırma:** Mutlak sayılar T5 nedeniyle birebir karşılaştırılamaz. Karşılaştırma **eğilim ve göreli
   iyileşme** düzeyinde yapılacak (ör. "w=0.7 en iyi mi?", "önerilen yöntem LEACH'e göre PDR'yi artırıyor mu?").

## 10. Sonraki adımlar (checkpoint eşlemesi)

| Checkpoint | Çıktı |
|---|---|
| **CP1 — Makale ve problem analizi** | ✅ Bu belge |
| CP2 — Uygulama planı | Kural tablosu, MF parametreleri, simülatör modelleri, deney planı; güncel literatür taraması (2023–2026) |
| CP3 — Baseline sistem | `src/` altında FIS + simülatör + PSO-GA; D1 ve D2 deneylerinin ilk sonuçları |
| CP4 — Katkı önerisi | Seçilen katkı(lar), hipotez ve başarı ölçütü |
| CP5 — Deneysel sonuçlar | Baseline ve önerilen yöntem tabloları, grafikler, istatistiksel testler |
| Final | Rapor (8–12 sayfa, IEEE), sunum, canlı demo |
