# Başvuru taslağı

Bu yalnızca taslak. Hiçbir şey gönderilmedi.

Kurallar: https://nearhackathon.com/HACKATHON.md. Göndermeden önce dosyayı yeniden oku, çünkü kurallar değişebilir.

Başvuru formu: https://nearhackathon.com/#apply

Son tarih: 2026-11-14 23:59 UTC. Başvuru sonradan düzenlenemez ve aynı repo ikinci kez gönderilemez. Yani tek hakkın var.

Bu dosyaya e-posta, NEAR adresi ya da doldurulmuş başvuru verisi yazıp commit etme. Kurallar da kişisel veri içeren başvuruyu commit etmemeni söylüyor.

## Göndermeden önce

- Repoyu herkese açık yap. Şu an özel. Başvuruda da açık olmalı, hakem süreci boyunca da açık kalmalı.
- Demo postunu yayınla ve linkini al.
- Herkese açık demo kurduysan en az 2026-11-18'e kadar, tercihen 2026-11-25'e kadar açık tut.
- Aşağıdaki durum cümlelerinin hâlâ doğru olduğunu kontrol et.

## Alanlar

- projectName: `nearagent`
- leadName: boş. Takım liderinin adını sen yaz, 2 ile 80 karakter arası.
- email: boş. Sen dolduracaksın. En fazla 160 karakter.
- size: `1` öneriyorum, çünkü git geçmişinde tek yazar var. Başka biri varsa değiştir. Yalnızca şu değerler geçerli: `1`, `2 - 4`, `4 - 6`, `6 - 8`, `8+`.
- tracks: `open`, `security`, `agents`, `realworld`. Aşağıdaki nota bak.
- nearAddress: boş. Sen dolduracaksın. Ödül buraya gelir. Mainnet hesabı olmalı, küçük harfle, 2 ile 64 karakter arası.
- projectUrl: boş. Sen dolduracaksın. Herkese açık repo linki.
- demoUrl: boş. Sen dolduracaksın. X'teki ana postun linki.
- idea: aşağıdaki metin.
- consent: boş. Aşağıdaki metni kabul edersen `true` olur.

Consent metni, aynen:

I agree that the organizers may use these details to review our submission and contact us about this hackathon.

## Listede olmayan zorunlu alan

API ile gönderilirse bir alan daha gerekir: `requestId`. Bu, gönderim anında bir kez üretilen bir UUID'dir. Ağ hatasında aynı değerle yeniden denenir. Formu elle doldurursan bununla uğraşmana gerek yok.

Başka alan ekleme. Özellikle `website` alanı dolu giderse başvuru spam sayılıp reddedilir.

## Track notu

Her track için dürüst değerlendirmem:

- `open`: uyuyor. Erişilebilirlik başka bir kategoriye tam oturmuyor.
- `security`: uyuyor. Politika okuma, bütçe sınırı ve tek adımda dondurma bu track'in konusu. Ama gerçek Agent API ile henüz denenmedi, yalnızca sahte API ile test edildi.
- `agents`: zayıf. Bu track kazanan, harcayan ve pazarlık eden ajanlar istiyor. Bizim ajanımızın takas ve çekim kodu var, ama gerçek ağda hiç işlem yapmadı.
- `realworld`: zayıf. Bu track maaş, fatura ve ödeme gibi bir şirketin yarın kullanacağı şeyler istiyor. Bizde kod hazır, ama yalnızca deneme modu gerçek serviste çalıştı.
- `privacy`: şimdilik ekleme. Kod NEAR AI Cloud'u önce deniyor, ama `.env` içinde NEAR AI anahtarı yok, cümleler şu an OpenAI'a gidiyor. Anahtarı ekleyip test setini NEAR AI ile de çalıştırırsan ekle. Kredi için https://cloud.near.ai adresine bak. NEAR Builders'a katılınca 10 dolar kredi veriliyor.
- `defi`: istemediğin ama düşünmeye değer bir seçenek. NEAR Intents üzerinden takas teklifi verdiği için `agents` ve `realworld`'den daha yakın. Ama bu track de çalışan takas bekliyor, bizim canlı takasımız gerçek ağda denenmedi.

## idea

Metin 1593 karakter. Sınır 20 ile 2000 arası.

Swap interfaces are visual: charts, popups, and icon-only buttons. A blind user on a screen reader often cannot tell what a swap will cost or what they will receive.

nearagent is an accessibility-first crypto assistant for NEAR Intents. It has one text box. You type or say a sentence in Turkish or English, such as "swap 2 NEAR to USDC", and it answers in short sentences that a screen reader reads aloud. Every quote is read in one fixed order: what you give, what you get, the guaranteed minimum, the fee, the time, and how long the quote is valid. Every step works from the keyboard. A confirmation is held on the server, works once, and expires with its quote. Amounts above 100 dollars are spelled out and confirmed first.

How NEAR fits in: NEAR Intents 1Click supplies token data, prices, and quotes in dry mode, so one sentence can price a swap across chains with no bridge screens. The NEAR Intents Agent API is built in for a policy-bound wallet: live swaps, withdrawals only to the owner's address, a daily budget, freezing in one step, and unfreezing only with a six digit code. A separate script sends NEAR from the owner account. The parser is built to try NEAR AI Cloud first, with OpenAI as the fallback.

Current status: dry mode is the default and works with the real 1Click API. Live swaps, withdrawals, freezing, and the NEAR send script are built, but they have only been tested against a local stand-in API and a fake RPC. None has run on a real network, and no agent is funded yet. Parsing has been measured with OpenAI only, on a test set that also shaped the prompt.

## idea metnini ne zaman değiştirmelisin

- Ajanı kurup fonlarsan son paragraftaki ajan cümlesini güncelle.
- NEAR AI Cloud'u ölçersen son cümleyi güncelle ve `privacy` track'ini ekle.
- Gerçek ağda bir takas, çekim ya da dondurma yaparsan yalnızca gerçekten denediğini yaz. Denenmeyeni denenmiş gösterme.
