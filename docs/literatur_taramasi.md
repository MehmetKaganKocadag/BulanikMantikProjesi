# Literatür Taraması

> Referans makale ve yapılan iki katkı (K1, K6) bağlamında 2022–2026 arası çalışmaların taraması. Kaynak
> numaraları [references/README.md](../references/README.md) ile aynıdır. Bütün künyeler Crossref'te DOI ile
> doğrulandı. Çalışmaların içeriği yalnızca yayıncı özetlerinden (abstract) aktarıldı; özeti bulunamayan
> çalışmalar için yalnızca başlıktan anlaşılan konu yazıldı ve bu belirtildi.

---

## 1. Kapsam ve yöntem

- **Konu:** WSN/IoT'de bulanık mantık tabanlı küme başı (CH) seçimi, metasezgisel (PSO, GA ve hibritleri)
  yönlendirme ve sağlık IoT uygulamaları.
- **Kaynaklar:**
  - Referans makalenin kaynakçasındaki ilgili çalışmalar [2]–[11].
  - Web taramasıyla bulunan 2022–2026 çalışmaları [26]–[32].
- **Doğrulama:** Her künye Crossref API'sinde DOI ile kontrol edildi. Taramada bulunan ama Crossref'te
  doğrulanamayan üç aday (bir 2025 Sci. Rep. type-2 bulanık yönlendirme makalesi, 2024 tarihli bir
  bulanık–genetik yönlendirme makalesi ve 2026 tarihli bir WBAN yönlendirme makalesi) kaynakçaya alınmadı.
- **Sınırlılık:** Çalışmaların tam metinleri değil özetleri okundu. Sayısal sonuçlar yazarların kendi
  bildirdiği değerlerdir; bu projede yeniden üretilmedi.

## 2. Bulanık mantık tabanlı CH seçimi

**Klasik temel.** Gupta, Riordan ve Sampalli [17], enerji, yoğunluk ve merkeziliği girdi alan Mamdani tipi
bir bulanık sistemle CH seçimini öneren ilk çalışmalardan biridir. Bu projedeki statik bulanık baseline (B2)
bu yaklaşımın karşılığıdır. LEACH [16], [25] ise rastgele, olasılıksal CH rotasyonunun standart referansıdır.

**Güncel incelemeler.** Verma ve arkadaşları [26], WSN'lerde bulanık kümeleme tekniklerini kapsamlı biçimde
inceler. Bulanık mantığın, sensör ömrünü etkileyen etkenlerdeki belirsizliği modellemek için kullanıldığını
vurgular. Woraphonbenjakul ve arkadaşları [32] da bulanık CH seçimi üzerine kısa bir güncel tarama sunar.
İki inceleme de alanın odağının enerji verimliliği ve ağ ömrü olduğunu gösteriyor.

**Bulanık + metasezgisel hibritler.** Son yıllardaki çalışmaların çoğu bulanık bir değerlendirmeyi bir
metasezgiselle birleştiriyor:
- Sennan ve arkadaşları [9]: bulanık tabanlı Harris şahinleri optimizasyonuyla CH seçimi (özet bulunamadı;
  konu başlıktan).
- Renaldo Maximus ve Balaji [11]: bulanık mantığı barnacle çiftleşme optimizasyonuyla birleştiriyor. Girdiler
  havuza ortalama uzaklık, küme içi ortalama uzaklık, kalan enerji ve CH denge faktörü.
- Hu ve arkadaşları [2] (QPSOFL): CH'leri kuantum PSO ile seçiyor. Bulanık sistemi ise bir sonraki atlama
  CH'sini belirlemek için kullanıyor (girdiler: kalan enerji, enerji sapması, aktarma uzaklığı).

**Tip-2 bulanık ve girdi normalizasyonu.** Yuste-Delgado ve arkadaşları [30], CH seçiminde aralık tip-2
bulanık sistem kullanır. Girdi değişkenlerinin normalizasyonunu, uç değerlerdeki dalgalanmaların etkisini
azaltmak için istatistiksel analize dayandırır. Bu, bu projede K1 kapsamında ele alınan sorunla doğrudan
ilişkili. Makalenin adaptif MF'si bölümlemeyi gözlenen min ve max değerlere bağlıyor; bu da dar dağılımlarda
küçük farkları büyütüyor (CP3 §8).

**Uyarlanabilir parametreler.** Hosseinzadeh ve arkadaşları [27], WBAN'larda DBSCAN'in parametrelerini
(Epsilon, MinPts) düğüm hızı ve RSSI'ya göre bir bulanık sistemle uyarlıyor. Referans makaledeki "ağ
koşullarına uyum" fikrinin farklı bir uygulaması.

## 3. Metasezgisel yönlendirme

**PSO tabanlı:**
- Lei [3]: bulanık kümeleme ile düğümleri gruplayıp gelişmiş PSO ile CH seçiyor. DEEC ve LEACH'e göre
  enerji tüketiminde %52 ve %16 azalma bildiriyor.
- Sikarwar ve Tomar [6] (MFCM-PSO): bulanık c-ortalamaların küme merkezlerini PSO ile iyileştiriyor. PSO
  küme ve CH sayısını seçiyor; çok atlamalı ağaç yönlendirme için ayrı uygunluk fonksiyonlarıyla seçilen
  ara CH'ler kullanılıyor (100 ve 200 düğüm).
- Sharmin ve arkadaşları [31] (HPSO-ILEACH): hibrit PSO'yu geliştirilmiş LEACH ile birleştirerek veri
  birleştirmeli kümelemede CH seçiyor.
- Tawfeek ve arkadaşları [10]: birbiriyle çelişen hedefleri (enerji dengesi, güvenilirlik, yük dağılımı, en
  kısa yol) bulanık çok amaçlı bir uygunlukla birleştiriyor ve yolları PSO ile optimize ediyor.

**GA ve hibritler:**
- Sikarwar ve Tomar [28] (HFCM-GA): hareketli düğümlü ağlarda küme oluşturmayı bulanık c-ortalamalar ve GA
  ile yapıyor.
- Prakash ve arkadaşları [7]: rota ve CH seçimini değiştirilmiş PSO ile GA'nın birleşimiyle yapıyor (özet
  bulunamadı; konu başlıktan).
- Ahmed ve arkadaşları [29]: kümeleme için kelebek optimizasyonu, yönlendirme için PSO kullanıyor (BOA-PSO).
  Karşılaştırmaya PSO-GA ve PSO-HAS gibi hibritleri de dahil ediyor. Yazarlar, bu tür hibrit protokollerin
  performansının ağ yapılandırmasına ve optimizasyon parametrelerine göre büyük ölçüde değiştiğini
  belirtiyor.

**Kesin yöntemlerle karşılaştırma.** Okunan özetlerin hiçbirinde metasezgisel yönlendirme Dijkstra gibi
kesin bir en kısa yol yöntemiyle karşılaştırılmıyor. Karşılaştırmalar LEACH, DEEC ya da başka metasezgisellerle
yapılıyor. Bu projede K6, PSO-GA'yı hem bileşenlerine ayırıp hem Dijkstra [18] ile karşılaştırıyor. Uygunluk
fonksiyonu neredeyse toplamsal olduğunda Dijkstra'nın aynı ağ performansını çok daha düşük maliyetle verdiği
gösteriliyor. PD yöntemindeki "iyi bir başlangıç çözümüyle başlatma" fikri, rastgele anahtar kodlamasının
[19] sağladığı esneklik sayesinde uygulanabiliyor.

## 4. Sağlık IoT

- **Othmen ve arkadaşları [8]:** IoT sağlık uygulamalarında enerji, uzaklık ve gecikme girdili bulanık CH
  seçimini PSO tabanlı yol seçimiyle birleştiriyor. Bildirilen sonuçlar: PDR %91.3, gecikme 0.12 s,
  throughput 60.1 bps, enerji verimliliği 8.9 J/bit. Referans makale [1] bu çalışmayı da kaynak gösteriyor ve
  çok yakın değerler bildiriyor (%92.5, 0.10 s, 61.5 bps, 9.1). Enerji verimliliğinin "J/bit" birimiyle ve
  "büyük daha iyi" olarak raporlanması iki çalışmada da ortak. Bu birim tutarsızlığı CP1'de (T5) tartışıldı.
- **Hosseinzadeh ve arkadaşları [27]:** WBAN'larda bulanık uyarlamalı DBSCAN (§2).
- **Hastalık tahmini çalışmaları:** Referans makalenin karşılaştırdığı ANFIS [5] ve GA-PSO [4] çalışmaları
  akciğer kanseri ve kalp hastalığı tahmini üzerine; yönlendirme protokolü değiller (CP1, T12).

## 5. Değerlendirme: bu projenin konumu

| Literatürdeki eğilim | Bu projedeki karşılığı |
|---|---|
| Bulanık değerlendirme + metasezgisel birleşimi yaygın; bileşenlerin ayrı katkısı nadiren ölçülüyor | K6: PSO-GA'nın PSO ve GA bileşenleri ayrı ayrı ve Dijkstra ile karşılaştırıldı |
| Karşılaştırmalar çoğunlukla LEACH/DEEC ya da diğer metasezgisellerle; kesin yöntem referansı yok | K6: kaba kuvvet optimumu (N = 20) ve Dijkstra referansı |
| Bulanık girdilerin normalizasyonu ve MF'lerin uyarlanması önemli bir tasarım sorunu [30], [27] | K1: adaptif MF'nin göreli değerlendirme sorunu, hibrit MF ve ağ ömrü deneyi |
| Hibritlerin performansı ağ yapılandırmasına duyarlı [29] | E6: "5/20" yorumunun ve yerleşimin sonuçlara etkisi test edildi |
| Okunan özetlerin hiçbirinde istatistiksel anlamlılık testi bildirilmiyor | Bütün deneylerde 30 tohum, eşleştirilmiş Wilcoxon ve Holm düzeltmesi [22], [23] |

Son satırdaki gözlem yalnızca okunan özetlere dayanıyor; tam metinlerde istatistiksel analiz yapılmış olabilir.
