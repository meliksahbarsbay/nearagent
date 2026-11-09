# Railway deploy hazırlık kontrolü

Tarih: 9 Kasım 2026. Bu dosya sadece kod okunarak hazırlandı. Hiçbir şey deploy edilmedi, Railway'e giriş yapılmadı, ağa istek atılmadı.

Hedef: herkese açık demoyu **yeni ve ayrı** bir Railway projesine koymak. Başka hiçbir Railway projesiyle (özellikle ReSLobby'ye ait olanlarla) servis, değişken ya da ortam paylaşılmaz.

Mevcut not dosyası `docs/deploy-railway.md` doğru ve hâlâ geçerli. Bu dosya onu kontrol listesine çevirir ve eksikleri ekler.

## 1. Mevcut durum

| Konu | Durum | Nerede |
|---|---|---|
| Builder | Railpack. Dockerfile, Procfile ve nixpacks.toml yok, gerekmiyor. Ama Railpack, `railway.json` içindeki `startCommand`'ı görmüyor (9 Kasım'da `railway up` ile doğrulandı). Başlatma komutu için `railpack.json` gerekli. | `railway.json:3-5`, `railpack.json` |
| Başlatma komutu | `python -m app.public_main` | `railway.json:7` |
| Port | `PORT` ortam değişkeni okunuyor, yoksa 8000. Host `0.0.0.0`. | `app/public_main.py:17` |
| Sağlık kontrolü | `/health`, 200 ve `{"status":"ok"}`. Koruma katmanı cevaplar, uygulamaya ve ağa gitmez. | `railway.json:9-10`, `app/demo_guard.py:282-283` |
| Kopya sayısı | 1. Sayaçlar bellekte, bu yüzden 1 kalmalı. | `railway.json:8` |
| Yeniden başlatma | Hata olursa, en çok 5 kez. | `railway.json:11-12` |
| Python sürümü | `3.10` | `.python-version:1` |
| Bağımlılıklar | `requirements.txt`, tam pin (`==`). 5 paket. | `requirements.txt:1-5` |
| Statik dosyalar | FastAPI `StaticFiles` ile `web/` klasöründen, `/` altında. Ayrı CDN ya da build adımı yok. | `app/main.py:95`, `app/main.py:866` |
| Koruma | Dakikalık ve günlük IP sınırı, günlük dil modeli bütçesi, 4096 bayt gövde sınırı, canlı mod kapalı, ajan anahtarları açılışta siliniyor. | `app/demo_guard.py` |
| CORS | Hiç CORS ayarı yok. Bu iyi: başka bir site tarayıcıdan JSON isteği atıp cevabı okuyamaz. | `app/main.py` içinde `CORSMiddleware` yok |
| Ses için sistem paketi | Gerekmiyor. Ayrıntı 5. bölümde. | |

Sonuç: Proje bugünkü haliyle Railway'de açılabilir. Aşağıdaki "yapılacaklar" listesi zorunlu olanları ve önerilenleri ayırır.

## 2. Railway'de tanımlanacak değişkenler (sadece adlar)

Değer yazılmadı. Değerleri sen Railway panelinde gireceksin.

### Dil modeli (en az biri, yoksa sadece form çalışır)

- `NEARAI_API_KEY` (eski adı `NEAR_AI_API_KEY` de çalışır, ikisini birden girme)
- `NEARAI_BASE_URL` (boş bırakılabilir, varsayılan NEAR AI Cloud adresi)
- `NEARAI_MODEL` (boş bırakılabilir. Not: `.env.example` bunu `NEAR_AI_MODEL` adıyla listeliyor, `app/intent.py:139` ikisini de okur)
- `OPENAI_API_KEY` (yedek, boş bırakılabilir)
- `OPENAI_MODEL` (boş bırakılabilir)

### 1Click teklif servisi

- `ONECLICK_BASE_URL` (boş bırakılabilir, varsayılan kodda)
- `ONECLICK_JWT` (isteğe bağlı, deneme modunda gerekmez)
- `INTENTS_ACCOUNT_ID` (deneme teklifleri için alıcı adı. Boşsa koddaki varsayılan kullanılır)

### Demo koruması (hepsi isteğe bağlı, varsayılanlar `docs/deploy-railway.md` içinde)

- `DEMO_RATE_PER_MINUTE`
- `DEMO_RATE_PER_DAY`
- `DEMO_DAILY_BUDGET_USD`
- `DEMO_LLM_INPUT_USD_PER_MTOK`
- `DEMO_LLM_OUTPUT_USD_PER_MTOK`
- `DEMO_LLM_RESERVE_USD`
- `DEMO_CLIENT_IP_HEADER`

### Açıkça kapalı tut

- `LIVE_ENABLED`: hiç girme ya da `false` gir. Koruma canlı modu zaten reddeder, bu ikinci kilit.

### Railway kendisi verir, elle girme

- `PORT`

### ASLA girme

`OWNER_PRIVATE_KEY`, `OWNER_PUBLIC_KEY`, `OWNER_ACCOUNT_ID`, `NEAR_INTENTS_AGENT_API_KEY`, `AGENT_API_KEY`, `AGENT_ID`, `GRANT_ID`, `GRANT_TOKEN`.

Koruma bunları açılışta siler (`app/demo_guard.py:32-41`, `app/demo_guard.py:324-325`). Yine de sunucuya hiç gelmemeleri gerekir. Railway'de "Raw Editor" ile toplu yapıştırma yaparken lokal `.env` dosyasını olduğu gibi kopyalama: içinde bu anahtarlar var.

### Girmenin anlamı olmayanlar

Herkese açık demoda kapalı oldukları için gereksiz: `NEARAI_REPAIR_MODEL`, `NEARAI_TRANSCRIBE_MODEL`, `REPAIR_PROVIDER`, `TRANSCRIBE_PROVIDER`, `REPAIR_MODEL`, `OPENAI_TRANSCRIBE_MODEL`, `MAX_LIVE_USD`, `MAX_LIVE_DAILY_USD`, `NEAR_INTENTS_AGENT_API_URL`, `NEAR_RPC_URL`, `EXPLORER_TX_URL`, `EXPLORER_INTENTS_URL`, `EXPLORER_ACCOUNT_URL`.

## 3. Yapılacaklar

### Zorunlu (deploy öncesi)

- [ ] **Yeni Railway projesi aç**, adı örneğin `nearagent-demo`. Mevcut bir projeye servis olarak ekleme. Özellikle ReSLobby projelerinin içine ekleme.
- [ ] **Başlatma komutunu değiştirme.** `uvicorn app.main:app` korumasızdır, herkese açık çalıştırılmaz (`docs/deploy-railway.md:15`).
- [ ] **Sağlayıcı hesaplarında aylık harcama sınırı koy** (NEAR AI Cloud ve OpenAI). Bellekteki günlük bütçe her yeniden başlatmada sıfırlanır (`app/demo_guard.py:4-5`).
- [ ] **Fiyat değişkenlerini gerçek model fiyatıyla gir.** Varsayılanlar kasıtlı olarak yüksek tahmin (`app/demo_guard.py:86-87`).
- [ ] **Uygulama uyutma (serverless / App Sleeping) kapalı kalsın.** Uyuyup uyanan servis sayaçları sıfırlar.
- [ ] **Kopya sayısı 1 kalsın**, yatay ölçekleme açma.
- [ ] **TCP proxy ve özel ağ erişimi açma.** Sadece Railway'in HTTPS alan adı. `X-Real-IP` başlığı başka yoldan taklit edilebilir (`docs/deploy-railway.md:49`).
- [ ] **Lokalde bir kez dene** (ağa çıkmaz, sadece açılışı test eder): `PORT=8080 python -m app.public_main`, sonra tarayıcıda `http://127.0.0.1:8080/health`. Bunu ben çalıştırmadım.

### Önemli (önerilen, kod değişikliği gerektirir)

Kodu değiştirmedim. Aşağıdakiler örnek diff olarak duruyor.

#### a) Python 3.10 desteği bitti

Python 3.10'un güvenlik desteği Ekim 2026'da sona erdi. Kod `str | None` gibi 3.10+ yazımı kullanıyor, 3.12'de çalışması beklenir. Önce lokalde testleri 3.12 ile çalıştır, geçerse:

```diff
--- a/.python-version
+++ b/.python-version
-3.10
+3.12
```

`docs/deploy-railway.md:11` de buna göre güncellenmeli.

#### b) `/docs`, `/redoc`, `/openapi.json` herkese açık

FastAPI bunları varsayılan olarak açar. Koruma sadece `/api/` yollarını sınırlar (`app/demo_guard.py:284`), bu sayfalar sınırsızdır ve tüm API şemasını gösterir. Gizli bilgi yok ama gereksiz yüzey. Sadece herkese açık sürümde kapatmak için `DemoGuard.__call__` içine:

```diff
--- a/app/demo_guard.py
+++ b/app/demo_guard.py
@@ class DemoGuard:
+    HIDDEN_PATHS = ("/docs", "/redoc", "/openapi.json")
+
     async def __call__(self, scope, receive, send):
         if scope["type"] != "http":
             return await self.app(scope, receive, send)
         if scope["path"] == "/health":
             return await self.answer(send, 200, {"status": "ok"})
+        if scope["path"].startswith(self.HIDDEN_PATHS):
+            return await self.answer(send, 404, {"error": "not_found"})
```

#### c) Güvenlik başlıkları yok

Hiçbir yanıtta `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`, `Strict-Transport-Security` yok. Sayfa sadece kendi `app.js` ve `voice.js` dosyalarını yüklüyor, satır içi `<style>` var ama satır içi script yok (`web/index.html:7-31`, `web/index.html:90-91`). Bu yüzden sıkı bir politika uyar. Örnek, `DemoGuard` içinde `send` sarmalayarak:

```python
SECURITY_HEADERS = [
    (b"content-security-policy",
     b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
     b"connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"microphone=(self), camera=(), geolocation=()"),
    (b"strict-transport-security", b"max-age=31536000"),
]

async def send_with_headers(message):
    if message["type"] == "http.response.start":
        message["headers"] = list(message.get("headers", [])) + SECURITY_HEADERS
    await send(message)
```

`DemoGuard.__call__` içinde `send` yerine `send_with_headers` kullanılır. Not: `Open in explorer` bağlantıları yeni sekmede açılır, CSP bunu etkilemez.

#### d) Herkese açık demoda NEAR AI ses tanıma seçeneği yanıltıcı

`/api/providers`, NEAR AI anahtarı varsa `near_ai: true` döner (`app/main.py:798`). Sayfa da ses tanıma menüsünde `NEAR AI (recommended)` gösterir (`web/app.js:272`). Oysa herkese açık demoda sunucu tarafı ses tanıma kapalı (`app/demo_guard.py:331`) ve 4096 bayt gövde sınırı kaydı zaten reddeder. Kullanıcı NEAR AI'yi seçerse `That request is too long. Try a shorter one.` duyar ve tarayıcıya düşer. Öneri:

```diff
--- a/app/main.py
+++ b/app/main.py
@@ async def providers_status():
     return {
         "transcribe": speech.available(),
         "repair": [...],
-        "near_ai": bool(near_ai_key()),
+        "near_ai": bool(near_ai_key()) and speech.allowed,
     }
```

Daha iyisi: `transcribe` listesi boşsa sayfa NEAR AI ve OpenAI seçeneklerini hiç göstermesin.

#### e) Herkese açık demoda ajan komutları "kurulmadı" diyor

`what's my balance`, `read my policy`, `withdraw all NEAR` herkese açık sayfada `The agent wallet is not set up. Try again after setup.` der (`app/messages.py:214`). Jüri bunu hata sanabilir. Ayrı bir mesaj öneririm (yalnızca demoda):

```text
This public demo has no agent wallet, so balance, policy, budget and withdraw are off here. The video shows them on a real agent. Swap quotes and prices work.
```

#### f) Beklenmeyen hata JSON değil

Yakalanmayan bir istisna FastAPI'nin düz metin `Internal Server Error` yanıtını verir. Sayfa `response.json()` yapamayınca `Could not reach the server` der (`web/app.js:509`, `web/app.js:531`). Kullanıcı sunucu kapalı sanır. Öneri: `main.py` içinde genel bir `@app.exception_handler(Exception)` ile `{"error": "server_error", "spoken": ...}` dönmek. Log'a sadece istisna türü yazılsın.

#### g) Bağımlılıklar

- `pytest==9.2.0` üretim imajına da kuruluyor. Zararsız ama gereksiz. İstersen `requirements-dev.txt` ayır.
- `pydantic` ve `starlette` doğrudan pinli değil, FastAPI'nin seçtiği sürüm gelir. Tekrarlanabilir build için `pip freeze` çıktısındaki sürümleri pinle.

```diff
--- a/requirements.txt
+++ b/requirements.txt
 fastapi==0.162.0
 httpx==0.28.1
 python-dotenv==1.2.4
 uvicorn==0.54.0
-pytest==9.2.0
+pydantic==<lokal .venv'deki sürüm>
+starlette==<lokal .venv'deki sürüm>
```

#### h) Küçük notlar

- Railway'in HTTPS'i otomatik. Mikrofon (`getUserMedia`, Web Speech) sadece güvenli bağlamda çalışır, bu yüzden HTTP alan adı kullanma.
- `history.json` ve `live_spend.json` herkese açık demoda kullanılmıyor (`app/demo_guard.py:327`), kalıcı disk (volume) gerekmez.
- `index.html` dosyası JavaScript çalışmadan önce `lang="tr"` ve Türkçe başlıkla gelir (`web/index.html:2`, `web/index.html:6`). Ayrıntı `docs/english-flow-audit.md` içinde.

## 4. Canlıda dikkat

### CORS

- Şu an CORS yok ve öyle kalmalı. `allow_origins=["*"]` asla ekleme.
- Sayfa ve API aynı alan adında, CORS'a ihtiyaç yok.
- Canlı mod herkese açık demoda iki kez kapalı. Başka bir siteden gelen istek de para hareket ettiremez.

### HTTPS

- Railway alan adı (`*.up.railway.app`) TLS ile gelir. Kendi alan adını bağlarsan sertifikanın aktif olduğunu kontrol et.
- HSTS başlığı önerilen diff (c) ile eklenir.
- Uygulamaya Railway dışında düz HTTP ile erişim açma (TCP proxy yok).

### Hız sınırı

- IP başına dakikada 20, günde 200 istek (varsayılan). Sadece `/api/` yolları sayılır.
- Sabit pencere: dakika sınırında kısa bir patlama iki katına çıkabilir (`app/demo_guard.py:106`). Kabul edilebilir.
- IP, `X-Real-IP` başlığından okunur. Railway bunu yazar ama sözleşmeyle garanti etmez. Yanlış gelirse ziyaretçiler aynı sayacı paylaşır. Para sınırı IP'ye bağlı değil, etkilenmez.
- Dil modeli için günlük toplam bütçe var. Bitince cümle çözümleme kapanır, form çalışmaya devam eder.
- 1Click teklif istekleri ücretsiz ama dış servise gider. IP sınırı bunları da sayar.
- Bellek sınırı: en çok 100.000 IP izlenir, fazlası tek sayaçta toplanır (`app/demo_guard.py:27`, `app/demo_guard.py:127-128`).

### Loglarda gizli bilgi sızıntısı

Kod okunarak bakıldı:

- Anahtarlar hiçbir yerde loglanmıyor. Sağlayıcı hataları sadece hata türü ve durum koduyla yazılıyor (`app/intent.py:266-268`, `app/agent_api.py:230`).
- Kullanıcının cümlesi loglanmıyor. Ses tanımada sadece karakter sayısı yazılıyor (`app/transcribe.py:119-123`).
- Dikkat: `app/oneclick.py:202` 1Click'in hata yanıtının ilk 300 karakterini yazıyor. Bu gizli anahtar içermez, ama teklifteki hesap adını içerebilir. `app/oneclick.py:188` ve `:199` httpx hatasını `%r` ile yazıyor, bu adres satırını içerir, başlıkları içermez. `ONECLICK_JWT` başlıkta gider, loga düşmez.
- `app/intent_repair.py:223-227` modelin önerdiği token adlarını yazıyor. Herkese açık demoda bu yol kapalı.
- Uvicorn erişim logu her isteğin yolunu yazar. Gövde yazılmaz. Sorgu dizesinde sadece `lang` ve `provider` var.
- Railway panelinde "Variables" ekranını ekran kaydına alma. Demo videosunda terminal ve `.env` görünmesin.
- Lokal `.env` dosyasını Railway "Raw Editor"e yapıştırma. İçinde sahip anahtarı var.

## 5. Ses tanıma için sistem paketleri

Gerekmiyor:

- Varsayılan ses tanıma tarayıcıda çalışır (Web Speech API). Sunucuya ses gelmez.
- Sesli yanıt da tarayıcıda üretilir (`speechSynthesis`, `web/voice.js:388-401`).
- Sunucu tarafı ses tanıma açık olsa bile ses dosyası olduğu gibi NEAR AI ya da OpenAI'ye iletilir, dönüştürme yapılmaz (`app/transcribe.py`). `ffmpeg` gerekmez.
- Herkese açık demoda sunucu tarafı ses tanıma kapalı (`app/demo_guard.py:331`).

Kullanıcıya not: Web Speech Chrome ve Edge'de çalışır, Firefox'ta çalışmaz. Chrome'da ses Google'a, Edge'de Microsoft'a gider. Sayfa bunu Gelişmiş bölümünde söylüyor (`web/app.js:126`).

## 6. Deploy sonrası kontrol (elle, sen yaparsın)

1. `https://<alan-adı>/health` 200 ve `{"status":"ok"}` dönüyor mu.
2. Sayfa açılıyor, NVDA başlığı ve "What do you want to do?" etiketini okuyor mu.
3. `what is 1 SOL worth` yazınca fiyat geliyor mu.
4. Gelişmiş bölümünden canlı modu açmayı dene: `Live mode is off in this public demo...` demeli.
5. 21 kez hızlıca gönder: 21. istekte dakika sınırı mesajı gelmeli.
6. Railway loglarında anahtar, cümle ya da `.env` değeri görünmüyor mu, bak.
