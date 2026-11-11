# Veri Setleri

Referans makale üç Kaggle veri seti kullanır (makaledeki kaynak no. [38]–[40]).
Veri dosyaları lisans ve boyut nedeniyle repoya **konmaz**; aşağıdaki adreslerden
indirilip `data/raw/` klasörüne yerleştirilmelidir.

| Kod | Ad | Kaggle adresi (makalede verildiği şekliyle) | İçerik |
|---|---|---|---|
| data1 | Healthcare IoT Data | https://www.kaggle.com/datasets/ziya07/healthcare-iot-data | Sıcaklık, kalp hızı, SpO2, solunum hızı (zaman damgalı, simüle) |
| data2 | Health Monitoring System | https://www.kaggle.com/datasets/prashantkumaryt/health-monitoring-system-analysis/data | Nabız, sistolik/diyastolik tansiyon, vücut sıcaklığı |
| data3 | Patient Temperature and Pulse Rate | https://www.kaggle.com/datasets/meghagoriya/patient-temperature-and-pulse-rate | Hasta kimliği, okuma zamanı, sıcaklık, nabız |

> ⏳ Her veri setinin lisansı ve sütun yapısı indirme sırasında kontrol edilip bu tabloya eklenecek.

## Beklenen klasör yapısı

```
data/
├── README.md        (bu dosya)
└── raw/             (gitignore'da — Kaggle'dan indirilen CSV dosyaları)
    ├── data1_healthcare_iot.csv
    ├── data2_health_monitoring.csv
    └── data3_patient_temp_pulse.csv
```

## Ön işleme (makalede tarif edilen)

Makaleye göre: eksik değerler medyan ile doldurulmuş, aykırı değerler z-skor ile
temizlenmiş, özellikler ölçeklenmiş ve zaman damgaları hizalanmıştır. Verinin ağ
parametrelerine (enerji, bağlantı kararlılığı vb.) **nasıl eşlendiği makalede
açıklanmamıştır**. Bu projede benimsenen eşleme `docs/checkpoint1_makale_analizi.md`
dosyasının 9. bölümünde ("Topoloji" satırı) tartışılmaktadır.
