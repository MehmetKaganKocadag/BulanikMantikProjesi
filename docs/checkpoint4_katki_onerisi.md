# Checkpoint 4 — Katkı Önerisi

> **Yönerge (CP4):** Ne değiştirileceği, neden değiştirileceği ve başarının nasıl ölçüleceği açık biçimde
> tanımlanacaktır.
>
> Seçilen katkılar **K1** (adaptif üyelik fonksiyonu, ağ ömrü boyunca) ve **K6** (yönlendirme ablasyonu).
> Bu belge deneyler çalıştırılmadan önce yazıldı. Hipotezler ve başarı ölçütleri sonuçlardan bağımsız olarak
> burada sabitlendi. Sonuçlar Checkpoint 5 belgesinde verilecek.

---

## 1. Özet

| | K1 — Hibrit adaptif MF ve ağ ömrü | K6 — Yönlendirme ablasyonu ve Dijkstra başlatmalı PSO-GA |
|---|---|---|
| Yönerge 6.1 karşılığı | Üyelik fonksiyonu yapısının değiştirilmesi; parametre optimizasyonu; yeni deney senaryosu | Farklı optimizasyon yöntemleriyle karşılaştırma; ablation study; hesaplama maliyeti |
| Ne değişiyor | Adaptif MF, statik MF'ye doğru ρ oranında çekiliyor (hibrit MF, **PH**) | PSO-GA'nın ilk parçacığı Dijkstra'nın yoluyla başlatılıyor (**PD**) |
| Neden | CP3'te adaptif MF önemsiz enerji farklarını büyüttü ve statik MF'den kötü çıktı | CP3'te PSO-GA neredeyse her zaman optimumda ama Dijkstra'dan 40–90 kat pahalı |
| Baseline | P (makalenin adaptif MF'si) ve B2 (statik MF) | P (makalenin PSO-GA'sı) |
| Ana ölçüt | Ağ ömrü boyunca BS'ye ulaşan toplam okuma sayısı | Rota uygunluğu, en iyi bilinen çözüme ulaşma oranı, hesaplama maliyeti |

## 2. K1 — Hibrit adaptif MF ve ağ ömrü

### 2.1 Gerekçe

Makalenin ana iddiası, MF'lerin ağın o anki durumuna göre uyarlanmasının CH seçimini iyileştirdiği. Makale bu
iddiayı statik MF ile karşılaştırarak hiç test etmiyor. CP3'te yapılan kontrollü karşılaştırma bunun tersini
gösterdi:

- 100 turluk koşularda adaptif MF (P), statik MF'den (B2) %1.5–3.8 daha kötü (CP3 §4).
- **Nedeni:** 100 turun sonunda düğüm enerjileri 0.91–0.98 gibi dar bir bantta kalıyor. Adaptif MF bu bandı
  bütün terim aralığına yayıyor; %95 enerjili bir düğüm "Düşük enerjili" sayılıyor. Değerlendirme göreli hale
  geliyor ve önemsiz farklar CH seçimine baskın geliyor (CP3 §8).
- Sabit CH sayılı yorumda da (CP3 §11) adaptif MF'nin üstünlüğü görülmedi.

Bu bulgulardan iki soru çıkıyor:

1. **Adaptasyon ne zaman işe yarar?** Kısa koşularda enerji farkı yok. Gerçek enerji farkları ağ ömrünün
   ilerleyen dönemlerinde ya da düğümler farklı pil seviyeleriyle başladığında oluşur. data1'deki cihaz pil
   seviyeleri %20 ile %100 arasında değişiyor, yani heterojen başlangıç gerçekçi bir senaryo.
2. **Göreli değerlendirmenin zararı azaltılabilir mi?** Adaptif MF dağılımı izlemeli ama küçük farkları
   abartmamalı.

### 2.2 Önerilen değişiklik: hibrit adaptif MF

Makalenin adaptif bölümlemesi her turda $(a, b, c)$'yi gözlenen dağılımdan hesaplar (a = min, b = medyan,
c = max, λ ile yumuşatma). Önerilen hibrit MF, bu adaptif üçlüyü statik bölümlemeyle (0, 0.5, 1) dışbükey
olarak birleştirir:

```math
(a, b, c)_{\text{hibrit}} = (1-\rho)(a, b, c)_{\text{adaptif}} + \rho(0, 0.5, 1), \qquad 0 \le \rho \le 1
```

- ρ = 0 makalenin adaptif MF'si, ρ = 1 statik MF'dir. Yani iki baseline da önerilen yöntemin özel durumlarıdır.
- Dışbükey birleşim sıralamayı korur (a < b < c). Ruspini bölümlemesi de korunur (üç üyeliğin toplamı 1).
- **Etkisi:** Dar bir enerji bandı artık bütün aralığa yayılmıyor, yalnızca kısmen genişliyor. Örneğin
  enerjiler 0.91–0.98 ve ρ = 0.5 iken bölümleme yaklaşık (0.46, 0.72, 0.99) olur. 0.91 enerjili düğüm hâlâ
  ağırlıklı olarak "Yüksek" kalır. Dağılım genişledikçe (ömrün sonlarına doğru) adaptif bileşen yine
  bilgi taşır.
- Yalnızca bölümleme değişiyor; girdiler, 81 kural, çıkarım ve durulaştırma aynı kalıyor.

### 2.3 ρ'nun seçimi (adil ayar)

ρ bir hiperparametre. Test tohumlarında ayarlanırsa önerilen yöntem haksız avantaj kazanır. Bu yüzden:

- ρ ∈ {0.25, 0.5, 0.75} değerleri **ayrı ayar tohumlarında** (100–109) denenir.
- Ayar ölçütü, ana ölçütün (§2.5) P'ye oranının bütün senaryolar ve veri setleri üzerindeki ortalamasıdır.
- Seçilen ρ, test tohumlarında (0–29) hiç değiştirilmeden kullanılır.

### 2.4 Deney düzeni

| | |
|---|---|
| Ağ | N = 50 düğüm, 100 × 100 m, BS merkezde, 25 m menzil (Tablo 3). N = 20'de CH'lerin %39'u bağlantısız olduğu için ağ ömrü bağlantıdan etkilenmesin diye N = 50 seçildi (CP3 §4.2) |
| Enerji | E₀ = 0.25 J (2 J ile ağ binlerce tur yaşar). İki senaryo: **homojen** (bütün düğümler 0.25 J) ve **heterojen** (E₀·(1 + U(−0.5, 0.5)), yani 0.125–0.375 J) |
| Süre | Son düğüm ölene kadar (LND), en çok 5000 tur |
| Yöntemler | B1 (LEACH + PSO-GA, referans), B2 (statik MF), P (adaptif MF, makale), **PH (hibrit MF)**; hepsi PSO-GA yönlendirme |
| Tekrar | 3 veri seti × 30 test tohumu; ayar için 10 ayrı tohum |
| Eşleştirme | Aynı tohumda topoloji, trafik ve heterojen başlangıç enerjileri bütün yöntemlerde aynı |

### 2.5 Ölçütler

| Ölçüt | Tanım | Rol |
|---|---|---|
| **Toplam teslim** | Ağ ölene kadar BS'ye ulaşan okuma sayısı | **Ana ölçüt.** Sağlık izlemede önemli olan, ağ ömrü boyunca ne kadar veri taşındığı |
| FND / HND / LND | İlk düğüm, düğümlerin yarısı ve son düğüm öldüğü tur | Klasik ağ ömrü ölçütleri (makalede yok, CP1 T17) |
| PDR, EE | E1 ile aynı | İkincil |
| CH sayısının değişkenliği | Turlar boyunca CH sayısının standart sapması | Kararlılık |

### 2.6 Hipotezler ve başarı ölçütü

- **H1a:** Ağ ömrü boyunca, özellikle heterojen senaryoda, adaptif MF (P) statik MF'den (B2) daha iyidir.
  Bu makalenin iddiasının test edilebilir biçimidir.
- **H1b:** Hibrit MF (PH), ana ölçütte P ve B2'nin ikisinden de kötü değildir.
- **Başarı ölçütü (PH için):**
  - 6 hücrenin (2 senaryo × 3 veri seti) en az yarısında PH, P'ye ya da B2'ye göre anlamlı biçimde daha iyi
    (Holm düzeltmeli Wilcoxon, p < 0.05).
  - Hiçbir hücrede ikisinden de anlamlı biçimde daha kötü değil.
- Başarı ölçütü sağlanmazsa sonuç olduğu gibi raporlanacak ve nedenleri tartışılacak (yönerge 6.2).

## 3. K6 — Yönlendirme ablasyonu ve Dijkstra başlatmalı PSO-GA

### 3.1 Gerekçe

Makale hibrit PSO-GA'yı ana yönlendirme yöntemi olarak sunuyor. GA bileşeninin katkısını ayrıca ölçmüyor,
algoritmayı kesin bir yöntemle de karşılaştırmıyor. CP3'te şunlar görüldü:

- PSO-GA, 20 düğümlü küçük grafiklerde kaba kuvvetle bulunan optimuma vakaların %99'unda ulaşıyor (CP3 §2.3).
- Uygunluk fonksiyonu neredeyse toplamsal. Bu yüzden toplamsal yaklaşık maliyetle çalışan Dijkstra çok yakın
  sonuç veriyor (%87–99 optimum) ve 40–90 kat daha hızlı.
- Ortalama rota 2–3 atlamalı; arama uzayı küçük.

Bu durumda iki soru var: (1) PSO-GA'nın her bileşeni gerçekten gerekli mi? (2) Dijkstra'nın hızı ile
PSO-GA'nın doğruluğu birleştirilebilir mi?

### 3.2 Önerilen değişiklik: Dijkstra başlatmalı PSO-GA (PD)

- Önce Dijkstra, uygunluğun toplamsal yaklaşımıyla bir yol bulur.
- Bu yol rastgele anahtar kodlamasına çevrilir ve sürünün ilk parçacığı olarak kullanılır. Yoldaki düğümlere
  azalan yüksek öncelikler, diğer düğümlere düşük öncelikler verilir; çözümleme tam olarak Dijkstra'nın
  yolunu üretir (birim testle doğrulandı).
- Geri kalan parçacıklar rastgeledir; PSO-GA olduğu gibi çalışır.
- **Garanti:** En iyi çözüm hiçbir zaman Dijkstra'nın yolundan kötü olamaz (birim testle doğrulandı).
- **Beklenen etki:** İyi bir başlangıç noktası, erken durma (20 iterasyon iyileşme yoksa dur) ile birlikte
  daha az değerlendirmede daha iyi sonuç vermeli.

### 3.3 Karşılaştırılan yöntemler

| Kod | Yönlendirme | Rolü |
|---|---|---|
| R0 | Doğrudan BS'ye | Çok atlamalı yönlendirmenin değeri |
| R1 | Dijkstra (toplamsal yaklaşık maliyet) | Kesin yöntem, en ucuz |
| R2 | Yalnızca PSO | GA bileşeninin katkısı |
| R3 | Yalnızca GA | PSO bileşeninin katkısı |
| P | PSO-GA (makale) | Baseline |
| **PD** | Dijkstra başlatmalı PSO-GA | Önerilen |

Hepsinde CH seçimi aynı (AFL) ve aynı parametreler kullanılıyor (30 parçacık, 100 iterasyon, sabır 20).

### 3.4 Deney düzeni

**A — Algoritma düzeyi:**
- N ∈ {20, 50, 100} düğüm, her biri için 30 rastgele topoloji.
- Her topolojide AFL'nin ilk turda seçtiği bütün CH'ler için her yöntem çalıştırılır.
- **En iyi bilinen çözüm:** N = 20'de bütün basit yolların kaba kuvvetle taranması (kesin optimum). N = 50 ve
  100'de bütün yöntemlerin ve uzun bir PSO-GA koşusunun (100 parçacık, 300 iterasyon) bulduğu en iyi yol.
- **Ölçütler:**
  - En iyi bilinen çözüme ulaşma oranı
  - Ortalama göreli uygunluk farkı
  - Uygunluk değerlendirme sayısı
  - CPU süresi
  - Yakınsama eğrisi (değerlendirme sayısına karşı en iyi uygunluk)

**B — Ağ düzeyi:**
- E1 ile aynı düzen: N ∈ {20, 50}, 100 tur, 3 veri seti × 30 tohum.
- Ölçütler: PDR, gecikme, EE, epoch başına yönlendirme süresi.

### 3.5 Hipotezler ve başarı ölçütü

- **H2a:** GA bileşeni PSO'ya katkı sağlar: P'nin en iyi çözüme ulaşma oranı R2'den yüksektir.
- **H2b:** Ağ düzeyinde R1 (Dijkstra), P ile aynı PDR ve EE'yi çok daha düşük maliyetle sağlar.
- **H2c:** PD, uygunlukta her zaman R1'den kötü değildir (bu bir garanti) ve en iyi çözüme P'den daha sık
  ulaşır.
- **Başarı ölçütü (PD için):**
  - Üç N değerinin hepsinde en iyi çözüme ulaşma oranı P'den yüksek ya da eşit.
  - Ortalama değerlendirme sayısı P'den düşük.
  - Ağ düzeyinde hiçbir ölçütte P'den anlamlı biçimde kötü değil.

## 4. Adil karşılaştırma ilkeleri

- **Aynı koşullar:** Bütün yöntemler aynı simülatörde, aynı parametrelerle ve aynı tohumlarla çalışır.
  Topoloji, trafik ve başlangıç enerjileri yöntemden bağımsız tohum akışlarından üretilir. Bu sayede
  karşılaştırmalar eşleştirilmiştir.
- **Ayrı ayar tohumları:** Önerilen yöntemin tek hiperparametresi (ρ) test tohumlarından ayrı tohumlarda
  seçilir.
- **Eşit bütçe:** PD ile P aynı parçacık, iterasyon ve sabır değerlerini kullanır. PD'nin Dijkstra
  aşamasının süresi de PD'nin maliyetine eklenir.
- **İstatistik:** Wilcoxon işaretli sıra testi, Holm düzeltmesi; ortalama ± %95 güven aralığı. Bütün testler
  ve ham sonuçlar CSV olarak yayımlanır.
- **Olumsuz sonuçlar da raporlanır.** Yönergeye göre önerilen yöntemin daha iyi olması zorunlu değil.

## 5. Uygulama durumu

| Bileşen | Dosya | Durum |
|---|---|---|
| Hibrit MF (`shrink` = ρ) | `src/afl_wsn/fuzzy/membership.py` | ✅ |
| Heterojen başlangıç enerjisi (`e_init_spread`) | `src/afl_wsn/config.py`, `simulator.py` | ✅ |
| Dijkstra başlatmalı PSO-GA (`pso_ga_ds`) | `src/afl_wsn/routing.py` | ✅ |
| Yeni yöntem kodları: PH, PD, R0 | `src/afl_wsn/experiment.py` | ✅ |
| Birim testleri (8 yeni, toplam 40) | `tests/test_contributions.py` | ✅ |
| K1 ve K6 deney betikleri | `experiments/proposed/run_k1.py`, `run_k6.py` | ✅ (sonuçlar: [Checkpoint 5](checkpoint5_deneysel_sonuclar.md)) |

Yeni parametrelerin varsayılan değerleri (ρ = 0, yayılım = 0, `pso_ga`) önceki davranışı birebir korur. E1
sonuçlarının değişmeden yeniden üretildiği kontrol edildi.
