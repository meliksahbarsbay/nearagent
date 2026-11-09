# İngilizce akış denetimi

Tarih: 9 Kasım 2026. Sadece kod okundu. Ağa istek atılmadı, kod değiştirilmedi.

Taranan dosyalar: `app/messages.py`, `app/main.py`, `app/demo_guard.py`, `app/commands.py`, `app/confirm.py`, `app/voice_text.py`, `app/live.py`, `app/amounts.py`, `app/intent.py`, `app/transcribe.py`, `web/index.html`, `web/app.js`, `web/voice.js`.

## Kısa sonuç

- İngilizce mesaj tablosu tam. `app/messages.py` içinde Türkçe her anahtarın İngilizce karşılığı var. Arayüz metinleri (`web/app.js:85-165`) de eksiksiz.
- Türkçe yanıt alınan yerler var ama hepsi kenar durumlar: varsayılan dil `tr` olan uç noktalar, sayfanın JavaScript'ten önceki hali ve sunucunun tahmin ettiği dile göre sayfanın kendiliğinden dil değiştirmesi.
- En büyük sorun dil değil, **komut kapsamı**: `freeze`, `stop the agent`, `what's my budget`, `policy` gibi doğal İngilizce ifadeler komut olarak tanınmıyor ve genel yardım mesajına düşüyor.
- Birkaç dil bilgisi hatası var: tekil ve çoğul (`1 assets`, `Last 1 trades`, `about 1 minutes`).

Önem: **Y** yüksek, **O** orta, **D** düşük.

## 1. Türkçe kalan ya da Türkçeye düşen yerler

| # | Önem | Dosya:satır | Sorun | Öneri |
|---|---|---|---|---|
| 1.1 | O | `web/app.js:521` | Sunucu her yanıtta `language` döner ve sayfa ona geçer. İngilizce kullanıcının kısa ya da belirsiz cümlesini model `tr` diye işaretlerse tüm arayüz sessizce Türkçeye döner. Ekran okuyucuya duyurulmaz. | Yeni cümlede dil seçimini sayfaya bırak: sayfa `lang` gönderiyorsa sunucu yanıtı o dilde versin. Ya da dil değişince `Language set to English.` gibi bir duyuru yap. |
| 1.2 | O | `app/demo_guard.py:231-235` | Hız sınırı, gövde sınırı ve canlı mod reddi mesajları gövdede `lang` yoksa `Accept-Language` başlığına bakar. Başlık `en` ile başlamıyorsa (Almanca, İspanyolca tarayıcı) **Türkçe** döner. GET `/api/providers` ve `/api/transcribe` gövdesinde `lang` yok. | Varsayılanı `en` yap ya da `?lang=` sorgusunu da oku: `return "tr" if accepted[:2].lower() == b"tr" else "en"`. |
| 1.3 | D | `app/main.py:120`, `:142`, `:147`, `:804` | `QuoteInput`, `ModeInput`, `TrackInput` ve `/api/transcribe` için varsayılan dil `tr`. Sayfa her zaman `lang` gönderdiği için kullanıcı etkilenmez, API'yi doğrudan kullanan biri Türkçe alır. | Varsayılanı `en` yap ya da `Accept-Language`'dan çıkar. |
| 1.4 | D | `web/index.html:2`, `:6` | JavaScript çalışmadan önce sayfa `lang="tr"` ve Türkçe başlık `nearagent: erişilebilir kripto asistanı` ile gelir. NVDA sayfa açılırken başlığı Türkçe sesle okuyabilir. JavaScript kapalıysa tüm etiketler boş kalır. | Statik HTML'i İngilizce yap (`lang="en"`, `<title>nearagent: an accessible crypto assistant</title>`) ve etiketlere İngilizce varsayılan metin koy. JS gelince Türkçeye geçer. |
| 1.5 | D | `web/app.js:750`, `:683`, `:711` | Onayla düğmesi sunucuya `evet`, Esc `iptal` gönderir. İki kelime de iki dilde tanındığı için çalışır. Kullanıcı duymaz. Sadece loglarda ve API izlemede karışık görünür. | Sayfa diline göre `yes` / `cancel` gönder. |
| 1.6 | D | `app/transcribe.py:36-37` | İpucu metni dile göre seçiliyor, sorun yok. Not olarak eklendi. | Değişiklik yok. |

## 2. Yanlış ya da yanıltıcı İngilizce metinler

| # | Önem | Dosya:satır | Şu an | Önerilen |
|---|---|---|---|---|
| 2.1 | O | `app/messages.py:299` (Türkçesi `:117`) | `OpenAI speech recognition is off, so I am using the browser's own.` NEAR AI seçiliyken de bu söyleniyor. | `Server speech recognition is off, so I am using the browser's own.` |
| 2.2 | O | `app/messages.py:218` (Türkçesi `:36`) | `...cannot go on to Binance from there. To return it, swap to NEAR first.` Jüri ve genel kullanıcı için kişisel kurulum ayrıntısı. | `Warning: this token stays on the owner account. To send it on to an exchange, swap it to NEAR first.` |
| 2.3 | O | `app/messages.py:217` | `All of it cannot go at once, so this is the limit for one transaction.` Anlamı belirsiz. | `The full balance is over the one transaction limit, so I will withdraw the limit only.` |
| 2.4 | O | `app/messages.py:219`, `:223` ile `:288` | `withdraw all NEAR` diyen kullanıcı `Arriving: about 1.2 wNEAR` ve `1.2 wNEAR went to your owner address` duyar, ama sonra `wNEAR arrives ... as native NEAR` notu gelir. Sıra kafa karıştırır, `wNEAR` sesli okunurken "w near" ya da "wuh-near" olur. | wNEAR için alınan tutarı `NEAR` diye söyle: `Arriving: about 1.2 NEAR, as native NEAR.` Spoken metinde `wNEAR` yerine `wrapped NEAR`. |
| 2.5 | O | `app/messages.py:237`, `:603` | `{assets} assets are allowed.` 1 olunca `1 assets are allowed.` | Tekil için ayrı anahtar: `1 asset is allowed.` |
| 2.6 | O | `app/messages.py:329` | `Last {count} trades.` 1 olunca `Last 1 trades.` | `Your last trade.` ve `Your last {count} trades.` |
| 2.7 | D | `app/messages.py:253`, `app/main.py:443` | `Try again in about {minutes} minutes.` En az 1 döndüğü için `about 1 minutes` olabilir. | 1 için `about a minute`. |
| 2.8 | D | `app/messages.py:357-358` | `{count} seconds` ve `{count} minutes`. `1 seconds` ya da `1 minutes` olabilir (`app/messages.py:499-502`). | Tekil biçim ekle. |
| 2.9 | O | `app/messages.py:330`, `:335` | Deneme işleminde: `Gave 1 NEAR, received 2.1 USDC, nothing executed.` "received" ile "nothing executed" çelişiyor. | Deneme satırı için ayrı kalıp: `Trade 1: November 9 at 14:05, dry run. Quote was 1 NEAR for 2.1 USDC. Nothing was executed.` |
| 2.10 | D | `app/messages.py:331`, `:647` | Tarih sunucunun saat diliminde. Railway'de UTC olur, kullanıcı bunu bilmez. | `November 9 at 14:05 UTC` ya da saati sayfada yerel saate çevir. |
| 2.11 | D | `app/messages.py:321-322` | `Your wallet is empty.` ve `In your wallet:` Bu ajanın cüzdanı, kullanıcının değil. Para hareketinde kimin cüzdanı olduğu net olmalı. | `The agent wallet is empty.` ve `The agent wallet holds:` |
| 2.12 | O | `app/messages.py:373-380` | Model `help` dediğinde yanıt sadece takas ve fiyattan söz eder. Bakiye, politika, çekim, dondurma ve sesli mod hiç geçmez. Tanınmayan her cümle buraya düşer (bkz. bölüm 3). | `I can quote swaps, read prices, read the agent's balance, policy and budget, withdraw to the owner address, and freeze the agent. For example: swap 2 NEAR to USDC, or what's my balance. Press Alt H for all shortcuts.` |
| 2.13 | D | `app/messages.py:368` | `How much do you want to convert?` Arayüzün geri kalanı "swap" diyor. | `How much do you want to swap?` |
| 2.14 | D | `app/messages.py:214` | `The agent wallet is not set up. Try again after setup.` Herkese açık demoda kullanıcı kurulum yapamaz. | Demoda: `This public demo has no agent wallet. The video shows balance, policy and withdraw on a real agent.` |

## 3. Komut kapsamı (İngilizce kullanıcı takılıyor)

Bu komutlar dil modeline gitmeden `app/commands.py` içindeki düzenli ifadelerle yakalanır. Yakalanmayan cümle modele gider. Model sadece `swap`, `price`, `help` bilir (`app/intent.py:93`), bu yüzden bakiye ya da dondurma isteği **genel yardıma** düşer.

| # | Önem | Dosya:satır | Yakalanmayan örnek | Öneri |
|---|---|---|---|---|
| 3.1 | Y | `app/commands.py:38` | `freeze`, `freeze it`, `stop the agent`, `pause the agent`, `stop everything`. Acil durdurma tek kelimeyle çalışmalı. | `re.compile(r"\bfreeze\b|\b(stop|pause|halt)\b.*\bagent\b|\bemergency stop\b")`. `unfreeze` önce kontrol edildiği için çakışmaz (`app/commands.py:31-35`). |
| 3.2 | O | `app/commands.py:21` | `what's my budget`, `budget`, `my budget`, `daily limit`. | `\bbudget\b|\bdaily (limit|cap)\b`. Not: `balance` anahtarından önce durduğu için sıra korunmalı. |
| 3.3 | O | `app/commands.py:17` | `policy`, `show policy`, `what are my limits`, `my rules`. | `\bpolicy\b|\b(my|the) (limits|rules)\b` |
| 3.4 | O | `app/commands.py:29` | `history`, `show my history`, `what did I trade`. | `\bhistory\b|\bwhat did i (trade|swap)\b` |
| 3.5 | D | `app/commands.py:25` | `how much do I have`, `my funds`, `check wallet`. Ayrıca çok geniş: `swap my balance to USDC` da bakiye okur. | `\bhow much (do i|does the agent) have\b|\bmy funds\b` ekle. `balance` tek başına kalabilir ama `swap` ile başlayan cümleyi hariç tut. |
| 3.6 | O | `app/confirm.py:19` | Bekleyen teklife `stop`, `nope`, `never mind` yazmak iptal etmez, `I did not understand your answer` döner. Sesli canlı onayda yine iptal olur ama "duyamadım" diye (`voice_unclear`). | `NO_WORDS`'e `stop`, `nope`, `nevermind`, `abort` ekle. |
| 3.7 | D | `app/confirm.py:18` | `ok`, `sure`, `yep`, `y` onay sayılmaz. Canlı mod için bu bilinçli bir katılık. Deneme modunda kullanıcı `I did not understand your answer. Say yes or no.` duyar. | Canlıda aynen kalsın. Hata mesajı zaten ne yapılacağını söylüyor. |
| 3.8 | D | `app/confirm.py:35` | Sesli canlı onayda sadece `yes I confirm` geçer. `I confirm` ya da `yes confirm` iptal eder. Mesaj tam ifadeyi söylediği için kabul edilebilir. | Değişiklik gerekmez. Demo videosunda tam ifade söylenmeli. |

## 4. Ekran okuyucu ve aria metinleri

| # | Önem | Dosya:satır | Sorun | Öneri |
|---|---|---|---|---|
| 4.1 | O | `web/app.js:107-114` (Türkçesi `:26-33`) | Kısayol ve yardım metinleri Alt S'yi (sesli mod) hiç söylemiyor. Sadece düğmede `aria-keyshortcuts="Alt+S"` var (`web/index.html:44`). | Kısayollara ekle: `Alt S turns voice mode on or off.` |
| 4.2 | D | `web/index.html:43` | Mikrofon düğmesinde `aria-keyshortcuts="Alt+M"` yok, sesli mod düğmesinde var. | `aria-keyshortcuts="Alt+M"` ekle. |
| 4.3 | D | `web/app.js:334` | Kopyala düğmesi `Quote ID: Copy` okunuyor. | `Copy quote ID` (fiil önce). Türkçede `Teklif kimliğini kopyala`. |
| 4.4 | O | `web/app.js:272`, `app/main.py:798` | Herkese açık demoda `NEAR AI (recommended)` görünür ama sunucu ses tanıma kapalı. Seçilirse kullanıcı `That request is too long. Try a shorter one.` duyar (`app/demo_guard.py:54`). | Sunucu kapalıysa seçeneği gösterme. Ayrıntı `docs/deploy-checklist.md` 3(d). |
| 4.5 | D | `web/app.js:123` | `Browser (Google)`. Edge'de servis Microsoft'tur. | `Browser (Google in Chrome, Microsoft in Edge)` ya da sadece `Browser`. |
| 4.6 | D | `web/app.js:106`, `:531` | Sunucu 500 döndüğünde de `Could not reach the server. Check that the app is running` denir. | Yanıt geldi ama JSON değilse: `Something went wrong on the server. Nothing was sent. Try again shortly.` |
| 4.7 | D | `web/app.js:57` | Türkçe `noVoice` sonunda nokta yok, İngilizcesinde var. NVDA duraklamayı farklı yapar. | Nokta ekle. |

## 5. Uçtan uca izleme

Her adım kod üzerinden izlendi. "Duyulan" metinler mesaj tablosundan kuruldu, tutarlar örnektir.

### 5.1 `swap 1 NEAR to USDC` (deneme modu, yazarak)

1. `web/app.js:719-725`: form gönderilir, gövde `{text, lang:"en", live:false}`.
2. `app/main.py:744-746`: komut değil. `detect_language` İngilizce der (`app/messages.py:453-455`).
3. `app/main.py:767`: dil modeli cümleyi çözer (NEAR AI, olmazsa OpenAI). `language` alanı modelden gelir.
4. `app/main.py:293-363`: 1Click'ten deneme teklifi. Duyulan:
   `Dry run. You give: 1 NEAR. You get: about 2.1 USDC. Guaranteed minimum: 2.09 USDC. Fee: about 0.01 dollars. Time: about 20 seconds. Quote valid for 10 minutes. I used USDC on NEAR; tell me if you want another chain. Do you confirm? Say yes or press Enter.`
5. Enter ya da `yes`: `app/main.py:520-524`. Duyulan: `Dry run: nothing was executed.`

Takılma noktaları:
- Model `language: "tr"` derse adım 4 tamamen Türkçe olur ve sayfa Türkçeye geçer (madde 1.1).
- Anahtar yoksa ya da herkese açık demoda günlük bütçe bittiyse, doğru cümle için bile `Did you mean: swap 1 NEAR to USDC? Say yes or no.` sorulur (`app/main.py:768-773`). Kullanıcı yanlış yazdığını sanabilir. Öneri: kurallar cümleyi tam okuduysa "did you mean" yerine `Sentence parsing is limited right now. I read: swap 1 NEAR to USDC. Say yes for a quote.`
- Sesli modda `one point five NEAR` doğru çevrilir (`app/voice_text.py:56-83`). `you ess dee see` gibi harf harf söylenen USDC yakalanmaz (`app/voice_text.py:15`), Chrome genelde `USDC` yazdığı için düşük risk.

### 5.2 `what's my balance`

1. `app/commands.py:25`: `balance` komutu, dil `en`.
2. `app/main.py:549-550`: ajan yoksa `The agent wallet is not set up. Try again after setup.` Herkese açık demoda her zaman bu olur (madde 2.14).
3. Ajan varsa `app/main.py:562-567` ve `app/messages.py:613-641`. Duyulan:
   `In your wallet: 1.207098 wNEAR, about 3.01 dollars. 0.1 USDC, about 0.1 dollars. About 3.11 dollars in total.`

Takılma noktaları: `wNEAR` sesli okunuşu (2.4), "your wallet" aslında ajanın cüzdanı (2.11). `how much do I have` gibi bir varyasyon genel yardıma düşer (3.5).

### 5.3 `withdraw all NEAR`

1. `app/commands.py:13`: `withdraw` komutu.
2. `app/main.py:551-556`:
   - `LIVE_ENABLED` kapalıysa: `The agent wallet for live mode is not set up. You can continue in dry mode.` Ajan kurulu olsa bile bu söylenir. Kullanıcı ajanın yok olduğunu sanabilir. Öneri: `Live mode is turned off on this server, so withdrawals are off.`
   - Sayfa canlı modda değilse: `A withdrawal uses real money, so nothing was sent. Turn on live mode in the Advanced section first.` Doğru ve net.
3. `app/live.py:621-655`: `all` kelimesi `ALL_WORDS` içinde (`app/amounts.py:40`), tüm bakiye seçilir. `NEAR`, `wNEAR` satırıyla eşleşir.
4. Duyulan (canlı):
   `Live mode, real money. Withdrawing: 1.207098 wNEAR. To: your owner address, on NEAR. Arriving: about 1.207098 wNEAR. Fee: under 0.01 dollars. This takes about 3.01 dollars from your daily budget, leaving 6.99 dollars. Quote valid for 2 minutes. wNEAR arrives at the owner account as native NEAR. Do you confirm? Type yes or press the Confirm button.`
5. Sesli modda soru şöyle değişir: `1.207098 wNEAR will be withdrawn to your owner address. To confirm, say yes I confirm. To stop, say cancel.` (`app/main.py:570-583`).
6. Sonuç: `Withdrawal done. 1.207098 wNEAR went to your owner address. The explorer link is in the Identifiers section.`

Takılma noktaları:
- Kullanıcı NEAR dedi, her yerde wNEAR duyuyor. Önemli not (native NEAR olarak ulaşır) en sonda, süre bilgisinden sonra geliyor (2.4).
- Bakiye tek işlem sınırını aşarsa ilk cümle `All of it cannot go at once...` (2.3).
- Ajan NEAR tutmuyorsa: `The agent does not hold that token, so nothing was sent. It holds: USDC.` Net.
- Ajan NEAR'ı birden fazla zincirde tutuyorsa: `Which one should I withdraw? Nothing was sent. Say it again with a token or chain name: ...` Net.

### 5.4 Ek: `freeze the agent` ve `freeze`

- `freeze the agent`: yakalanır, onaysız imzalanır (`app/main.py:748-751`). Duyulan: `The agent is frozen and can do nothing. To resume, say unfreeze the agent.`
- `freeze` ya da `stop the agent`: yakalanmaz, modele gider, genel yardım döner. Acil durumda kullanıcı ajanın durduğunu sanabilir. **En kritik İngilizce akış hatası bu** (3.1).

## 6. Öncelik sırası

1. 3.1 Acil durdurma kelimeleri (`freeze`, `stop the agent`).
2. 1.1 Sayfanın sessizce dil değiştirmesi.
3. 2.12 ve 3.2-3.4 Genel yardım mesajı ve eksik komut varyasyonları.
4. 2.4 wNEAR / NEAR karışıklığı ve çekim cümle sırası.
5. 1.2 Bilinmeyen tarayıcı dilinde Türkçe hata mesajı.
