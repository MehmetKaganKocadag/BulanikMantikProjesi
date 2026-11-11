# Veri Setleri

Referans makale üç Kaggle veri seti kullanır (makaledeki kaynak no. [38]–[40]). Veri dosyaları lisans ve boyut
nedeniyle repoya **konmaz**. Aşağıdaki adreslerden indirilip bu klasöre, tablodaki dosya adlarıyla
yerleştirilmelidir.

| Kod | Ad | Kaggle adresi (makalede verildiği şekliyle) | Projede kullanılan dosya |
|---|---|---|---|
| data1 | Healthcare IoT Data | https://www.kaggle.com/datasets/ziya07/healthcare-iot-data | `data1_healthcare_iot_5000.csv` |
| data2 | Health Monitoring System | https://www.kaggle.com/datasets/prashantkumaryt/health-monitoring-system-analysis/data | `data2_health_monitoring.csv` |
| data3 | Patient Temperature and Pulse Rate | https://www.kaggle.com/datasets/meghagoriya/patient-temperature-and-pulse-rate | `data3_patient_temp_pulse.csv` |

> data1 sayfasında 200 ve 5000 satırlık iki dosya bulunur. **5000 satırlık sürüm** kullanılır. Makale bu veri
> setini "thousands of time-stamped entries" diye tanımlıyor. Ayrıca 20 düğüm × 100 tur = 2000 okuma
> gerekiyor; 200 satır bunun için yetersiz. 200 satırlık dosya (`data1_healthcare_iot.csv`) yalnızca hızlı
> testler için tutulur.

## İçerik (indirilen dosyalar incelenerek çıkarıldı)

### data1 — Healthcare IoT Data (5000 × 13)

| Sütun | Aralık | Not |
|---|---|---|
| `Patient_ID` | 490 farklı hasta | Hasta başına ort. 10.2 kayıt (en az 2, en fazla 28) |
| `Timestamp` | 2024-01-01 → 2024-07-27, saatlik | Her satırın zamanı farklı |
| `Sensor_ID`, `Sensor_Type` | 1–4; Battery / Temperature / Blood Pressure / Heart Rate | Neredeyse eşit dağılım |
| `Temperature (°C)` | 35.0–39.0 | |
| `Systolic_BP (mmHg)` / `Diastolic_BP (mmHg)` | 80–180 / 50–115 | |
| `Heart_Rate (bpm)` | 45–130 | |
| `Device_Battery_Level (%)`, `Battery_Level (%)` | 15–100 | Cihaz pil seviyesi |
| `Target_*`, `Target_Health_Status` | Healthy / Unhealthy | Sınıflandırma etiketi; bu projede kullanılmaz |

Eksik değer yoktur.

### data2 — Health Monitoring System (150 × 6)

| Sütun | Aralık | Not |
|---|---|---|
| `Sl.No` | 1–150 | Sıra no |
| `Patient ID` | 1, 2 | **Yalnızca 2 hasta**, satırlar dönüşümlü |
| `Temperature Data` | 32–48 | 119 satır 32; 40–48 arası değerler fizyolojik değil (ham sensör olası) |
| `ECG Data` | 0–138 | Ham değer, çoğu 0 |
| `Pressure Data` | 75–78 | 135 satır 77; sistolik/diyastolik ayrımı yok |
| `Target` | 0, 1, 2 | Etiket; kullanılmaz |

Eksik değer yoktur.

### data3 — Patient Temperature and Pulse Rate (156 × 3)

| Sütun | Aralık | Not |
|---|---|---|
| `Temp` | 28.44–41.81 | |
| `Pulse` | 0–4095 | **bpm değil, 12-bit ham ADC değeri.** 8 satır 0 (sensör kopması), 25 satır 4095 (doyma) |
| `Time` | 17:43:24 → 18:28:50 | ~15 s aralıklı, tek oturum. **Hasta kimliği yok** |

> **Makaleyle uyumsuzluk:** Makale data1'de SpO2 ve solunum hızı, data2'de sistolik/diyastolik tansiyon,
> data3'te hasta kimliği olduğunu söyler. İndirilen dosyalarda bunların hiçbiri yoktur
> (bkz. [Checkpoint 1, T18](../docs/checkpoint1_makale_analizi.md#73-teknik-hatalar-ve-tutarsızlıklar)).

## Ön işleme

Makalenin tarif ettiği adımlar (s. 9) uygulanır:

1. **Geçersiz ölçümler eksik sayılır:** data3'te `Pulse` = 0 ya da 4095, data2'de fizyolojik aralık dışındaki
   sıcaklıklar.
2. **Eksik değerler** sütun medyanıyla doldurulur.
3. **Ölçekleme:** Her sayısal sütun z-skor ile standartlaştırılır. |z| > 3 olan değerler aykırı kabul edilip
   medyanla değiştirilir.
4. **Sıralama:** Satırlar zaman damgasına göre sıralanır (data1: `Timestamp`, data2: `Sl.No`, data3: `Time`).

## Ağa nasıl bağlanır

Veriler **trafik kaynağı** olarak kullanılır (ayrıntı:
[Checkpoint 2, §3.5](../docs/checkpoint2_uygulama_plani.md#35-trafik-ve-veri-setlerinin-kullanımı)):

- Her düğüm, sıralı kayıt akışını kendine özgü bir başlangıç noktasından (ofset) okur.
- Her tur bir sonraki kaydı alır.
- Ölçüm belirgin değişirse, z-skora göre anormalse ya da uzun süredir paket göndermemişse paket üretir.

Böylece veri setleri ağ yükünü ve dolayısıyla enerji ve gecikmeyi belirler.
