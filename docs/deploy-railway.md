# Railway'e deploy notları

Bu dosya herkese açık demo içindir. Henüz deploy yapılmadı.

Yeni ve ayrı bir Railway projesi aç. ResLobby projelerini kullanma.

## Nasıl çalışır

- `railway.json` başlatma komutunu verir: `python -m app.public_main`.
- Bu komut `PORT` değerini kendisi okur.
- Railway Python 3.10 kullanır. `.python-version` bunu söyler.
- Sağlık kontrolü `/health` adresine gider.
- Dockerfile gerekmedi.

`app.public_main`, normal uygulamayı `app/demo_guard.py` korumasıyla sarar. Lokal komut olan `uvicorn app.main:app` korumasızdır. Onu asla herkese açık çalıştırma.

## Girilecek değişkenler

Zorunlu olan tek şey bir dil modeli anahtarı. O da yoksa sadece form çalışır.

- `NEAR_AI_API_KEY`: önce bu denenir.
- `OPENAI_API_KEY`: yedek sağlayıcı. Boş bırakılabilir.

Koruma ayarları. Hepsi isteğe bağlı, parantez içi varsayılan değer:

- `DEMO_RATE_PER_MINUTE` (20): bir IP'nin dakikalık istek sınırı.
- `DEMO_RATE_PER_DAY` (200): bir IP'nin günlük istek sınırı.
- `DEMO_DAILY_BUDGET_USD` (1): tüm sağlayıcılar için günlük toplam harcama sınırı, dolar. 0 verirsen cümle çözümleme kapanır.
- `DEMO_LLM_INPUT_USD_PER_MTOK` (5): bir milyon girdi jetonunun fiyatı, dolar.
- `DEMO_LLM_OUTPUT_USD_PER_MTOK` (20): bir milyon çıktı jetonunun fiyatı, dolar.
- `DEMO_LLM_RESERVE_USD` (0.01): her çağrı başlamadan ayrılan tutar. Maliyet bilinmezse bu tutar harcanmış sayılır.
- `DEMO_CLIENT_IP_HEADER` (x-real-ip): gerçek IP'yi veren başlık. Boş verirsen bağlantı adresi kullanılır.

İki fiyat varsayılanı gerçek fiyat değil. Kasıtlı olarak yüksek bir tahmindir. Deploy öncesi kullandığın modelin gerçek fiyatını gir. İki sağlayıcı aynı fiyatı kullanır, bu yüzden pahalı olanın fiyatını yaz.

## Asla girme

Şu değişkenleri Railway'e ekleme: `OWNER_PRIVATE_KEY`, `OWNER_ACCOUNT_ID`, `OWNER_PUBLIC_KEY`, `NEAR_INTENTS_AGENT_API_KEY`, `AGENT_API_KEY`, `AGENT_ID`, `GRANT_ID`, `GRANT_TOKEN`.

Girsen bile koruma açılışta bunları siler. Yine de sahip anahtarının sunucuda durması için bir sebep yok.

Bu şart. Uygulamada `ajanı dondur` komutu onay istemez. Anahtarlar sunucuda kalsaydı, siteyi açan herkes ajanı dondurabilirdi.

## Bilinen sınırlar

- Sayaçlar bellekte durur. Her yeniden başlatma ve deploy, harcama sayacını da sıfırlar. Bu yüzden sağlayıcı hesabında da aylık harcama sınırı koy. Asıl son güvence odur.
- Tek işlem, tek kopya çalışmalı. Kopya sayısını artırırsan her kopya kendi sınırını sayar.
- Railway `X-Real-IP` başlığını kendi yazıyor, ama bunu sözleşmeyle garanti etmiyor. Bazı kullanıcılar CDN katmanında IP'nin yanlış geldiğini bildirdi. O durumda birçok ziyaretçi aynı sınırı paylaşır. Harcama sınırı IP'ye bağlı olmadığı için bundan etkilenmez.
- Servise özel ağdan ya da TCP proxy ile erişim açma. O yollarda başlık taklit edilebilir.
- Herkese açık demoda ajan komutları `Ajan cüzdanı kurulmadı` der. Video sahne 3 bu yüzden lokalde çekilir.
