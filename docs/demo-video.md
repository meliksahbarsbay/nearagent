# Demo videosu senaryosu

Toplam süre 2 dakika. Üç sahne var. Türkçe ve İngilizce için iki ayrı kayıt al.

Anlatıcı NVDA konuşurken susar. Bu videonun asıl sesi NVDA'dır.

## Çekimden önce

- Sahne 3 şu an çekilemez. Bu projede ajan kurulu değil, `.env` içinde yalnızca `OPENAI_API_KEY` var. Komut bugün `Ajan cüzdanı kurulmadı` der. Önce README'deki fonlama adımlarını bitir. Bu adımlar gerçek para ister: yaklaşık 0,1 NEAR ve 10 USDC.
- Sahne 3'ü lokalde çek: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Herkese açık adres ajan komutlarını çalıştırmaz.
- Sahneler 1 ve 2 için de aynı lokal uygulamayı kullan. Böylece tek seferde çekilir.
- Fiyatlar değişir. Aşağıdaki `...` yerleri kayıtta gerçek değerle dolar.
- Yalnızca tarayıcı penceresini kaydet. Terminal ve `.env` görünmesin.
- NVDA hızını biraz artır. Teklif cümlesi uzundur, sahne 1'in süresini belirler.
- Kulaklık tak. Hoparlörden çıkan NVDA sesi mikrofona girebilir.
- Mikrofon gerçek sesle henüz test edilmedi. NVDA ile Esc, Alt+R ve mikrofon maddeleri de README'de doğrulanmamış görünüyor. Önce bir deneme yap.
- Sahne 3'ü bir kez çek. Dondurduktan sonra çözmek için 10 dakika bekleme süresi var.
- Dondurma yanıtı 30 saniyeye kadar sürebilir. Kayıtta kısaltırsan ekrana `Bekleme kısaltıldı` yaz.

## Türkçe senaryo

### Sahne 1: NVDA ile klavyeden takas, deneme modu (0:00 - 0:55)

Anlatıcı (0:00): "Takas ekranları göz için yapılmış. Ekran okuyucuyla ne ödeyeceğini bile anlayamazsın. nearagent bunu tek cümleye indirir."

Ekranda: nearagent sayfası açık. Odak metin kutusunda. NVDA `Ne yapmak istiyorsun?` etiketini okur.

Ekranda: `2 NEAR'ı USDC'ye çevir` yazılır, Enter'a basılır. Fare kullanılmaz.

NVDA okur: "Deneme modu. Veriyorsun: 2 wNEAR. Alıyorsun: yaklaşık ... USDC. En az garanti: ... USDC. Ücret: yaklaşık ... dolar. Süre: yaklaşık ... Teklif 10 dakika geçerli. Onaylıyor musun? Evet de ya da Enter'a bas."

Not: Uygulama zincir seçtiyse araya bunu söyleyen kısa bir cümle girer.

Anlatıcı: "Sıra hep aynı. Ne veriyorsun, ne alıyorsun, en az ne garanti, ücret ne."

Ekranda: Boş kutuda Enter'a basılır.

NVDA okur: "Deneme modu: işlem yapılmadı."

### Sahne 2: Sesli komut (0:55 - 1:25)

Anlatıcı: "Yazmak istemezsen söyle."

Ekranda: Alt+M'ye basılır.

NVDA okur: "Dinliyorum"

Kullanıcı söyler: "bir SOL kaç dolar"

NVDA okur: "Anladım: ..." Duyulan cümle metin kutusuna yazılır.

Anlatıcı: "Kendi kendine göndermez. Önce sen kontrol edersin."

Ekranda: Enter'a basılır.

NVDA okur: "1 SOL yaklaşık ... dolar. Solana üzerindeki SOL'u kullandım; başka zincir istersen söyle."

### Sahne 3: Politika okuma ve ajanı dondurma (1:25 - 2:00)

Anlatıcı: "Ajan kurallarla çalışır. Kuralları da duyarak öğrenirsin."

Ekranda: `politikamı oku` yazılır, Enter'a basılır.

NVDA okur: "Politika: izinli işlemler takas ve çekim. 5 varlık izinli. Günlük bütçe 10 dolar. Ajan çalışır durumda."

Anlatıcı: "Bir şey ters giderse tek cümle yeter."

Ekranda: `ajanı dondur` yazılır, Enter'a basılır.

NVDA okur: "Ajan donduruldu, hiçbir işlem yapamaz. Açmak için ajanı çöz de."

Anlatıcı: "Bu sadece API onaylayınca söylenir. nearagent, NEAR Intents ve NEAR AI Cloud ile NEAR HACKATHON için yapıldı."

Ekranda: Proje adı ve GitHub adresi yazılır.

## English script

The Turkish reply text changes with the page language. Before recording, open the Advanced section and set the language to English, so that voice input listens in English.

### Scene 1: Keyboard swap with NVDA, dry mode (0:00 - 0:55)

Narrator (0:00): "Swap screens are built for eyes. On a screen reader, you may not even learn what a swap costs. nearagent puts it in one sentence."

On screen: The nearagent page is open, with focus in the text box. NVDA reads the label `What do you want to do?`

On screen: Type `swap 2 NEAR to USDC` and press Enter. No mouse is used.

NVDA reads: "Dry run. You give: 2 wNEAR. You get: about ... USDC. Guaranteed minimum: ... USDC. Fee: about ... dollars. Time: about ... Quote valid for 10 minutes. Do you confirm? Say yes or press Enter."

Note: If the app picked a chain, a short sentence saying so comes before the question.

Narrator: "Always the same order. What you give, what you get, the guaranteed minimum, and the fee."

On screen: Press Enter on the empty box.

NVDA reads: "Dry run: nothing was executed."

### Scene 2: Voice command (0:55 - 1:25)

Narrator: "If you would rather not type, just say it."

On screen: Press Alt+M.

NVDA reads: "Listening"

User says: "what is one SOL worth"

NVDA reads: "I heard: ..." The sentence appears in the text box.

Narrator: "It never sends by itself. You check it first."

On screen: Press Enter.

NVDA reads: "1 SOL is about ... dollars. I used SOL on Solana; tell me if you want another chain."

### Scene 3: Reading the policy and freezing the agent (1:25 - 2:00)

Narrator: "The agent works within rules, and you can hear those rules."

On screen: Type `read my policy` and press Enter.

NVDA reads: "Policy: allowed actions are swap and withdraw. 5 assets are allowed. The daily budget is 10 dollars. The agent is active."

Narrator: "If anything goes wrong, one sentence is enough."

On screen: Type `freeze the agent` and press Enter.

NVDA reads: "The agent is frozen and can do nothing. To resume, say unfreeze the agent."

Narrator: "It only says that after the API confirms it. nearagent uses NEAR Intents and NEAR AI Cloud, and was made for NEAR HACKATHON."

On screen: The project name and GitHub address.
