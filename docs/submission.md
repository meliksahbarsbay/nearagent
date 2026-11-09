# Başvuru taslağı

Bu yalnızca taslak. Hiçbir şey gönderilmedi.

Kurallar: https://nearhackathon.com/HACKATHON.md. Göndermeden önce dosyayı yeniden oku, çünkü kurallar değişebilir.

Başvuru formu: https://nearhackathon.com/#apply

Son tarih: 2026-11-14 23:59 UTC. Başvuru sonradan düzenlenemez ve aynı repo ikinci kez gönderilemez. Yani tek hakkın var.

Bu dosyaya e-posta, NEAR adresi ya da doldurulmuş başvuru verisi yazıp commit etme. Kurallar da kişisel veri içeren başvuruyu commit etmemeni söylüyor.

## Göndermeden önce

- Repoyu herkese açık yap. Şu an özel. Başvuruda da açık olmalı, hakem süreci boyunca da açık kalmalı.
- e-posta: bilerek açık bırakıldı. Commit bilgisindeki adres public olunca görünür, geçmiş yeniden yazılmadı.
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
- `security`: uyuyor. Politika okuma, bütçe sınırı ve tek adımda dondurma bu track'in konusu. Dondurma ve çözme gerçek Agent API'de bir kez çalıştı. 9 Kasım'da gerçek ağda bir çekim yapıldı: 0,1 NEAR sahip hesabına ulaştı.
- `agents`: zayıf. Bu track kazanan, harcayan ve pazarlık eden ajanlar istiyor. Bizim ajanımız gerçek ağda bir takas yaptı, ama kendi başına karar vermiyor, her işlemi sahibi onaylıyor.
- `realworld`: zayıf. Bu track maaş, fatura ve ödeme gibi bir şirketin yarın kullanacağı şeyler istiyor. Gerçek ağda bir takas yapıldı, ama maaş ya da fatura gibi bir kullanım yok.
- `privacy`: artık eklenebilir. 7 Kasım'da test seti NEAR AI ile ölçüldü. 44 cümlenin 43'ünü NEAR AI tek başına doğru çözdü. Biri 30 saniyede cevap gelmeyince OpenAI yedeğine düştü, o da doğru çözüldü. Cümleler artık önce NEAR AI'ın TEE'sine gidiyor. 9 Kasım'da öneri ve ses tanıma da NEAR AI ile kısa bir testten geçti. Öneri bozuk 5 cümlenin 5'ini doğru düzeltti, medyan 1,5 saniye. Ses tanıma bilgisayar sesiyle üretilmiş 4 İngilizce kaydın 2'sini tam doğru yazdı. Gerçek insan sesi ve Türkçe ses denenmedi.
- `defi`: istemediğin ama düşünmeye değer bir seçenek. NEAR Intents üzerinden takas teklifi verdiği için `agents` ve `realworld`'den daha yakın. Bu track çalışan takas bekliyor. Gerçek ağda bir takas yapıldı, 4,9 USDC'den 1,207 wNEAR'a. Tek bir takas olduğunu unutma.

## idea

Metin 1988 karakter. Sınır 20 ile 2000 arası.

Swap interfaces are visual: charts, popups, and icon-only buttons. A blind user on a screen reader often cannot tell what a swap will cost or what they will receive.

nearagent is an accessibility-first crypto assistant for NEAR Intents. It has one text box. You type or say a sentence in Turkish or English, such as "swap 2 NEAR to USDC", and it answers in short sentences that a screen reader reads aloud. Every quote is read in one fixed order: what you give, what you get, the guaranteed minimum, the fee, the time, and how long the quote is valid. Every step works from the keyboard. A confirmation is held on the server, works once, and expires with its quote. Amounts above 100 dollars are spelled out and confirmed first.

How NEAR fits in: NEAR Intents 1Click supplies token data, prices, and quotes in dry mode, so one sentence can price a swap across chains with no bridge screens. The NEAR Intents Agent API is built in for a policy-bound wallet: live swaps, withdrawals only to the owner's address, a daily budget, freezing in one step, and unfreezing only with a six digit code. A separate script sends NEAR from the owner account. NEAR AI Cloud is the first provider for parsing, for "did you mean" suggestions when speech garbles a token name, and for speech to text with Whisper in its TEE. OpenAI is an automatic backup.

Current status: dry mode is the default and works with the real 1Click API. On NEAR mainnet, through the Agent API's demo server, an agent was created, funded with 5 USDC, frozen and unfrozen. On 5 November it made one real swap, 4.9 USDC to 1.207 wNEAR, confirmed from the page with the NVDA screen reader. Proof links are in the README. On 9 November it withdrew 0.1 NEAR to the owner account. The NEAR send script was only tested locally. NEAR AI Cloud parsed 43 of 44 test sentences itself. One timed out, and the OpenAI backup got it right. That set also shaped the prompt. It also fixed 5 of 5 garbled sentences, in 1.5 seconds at the median.

## idea metnini ne zaman değiştirmelisin

- NEAR gönderim betiği gerçek ağda çalışırsa son paragrafı güncelle.
- Ses tanıma gerçek bir sesle ve Türkçe denenirse sonucunu ekle. Şu an yalnızca öneri sonucu metinde.
- Gerçek ağda bir takas, çekim ya da dondurma yaparsan yalnızca gerçekten denediğini yaz. Denenmeyeni denenmiş gösterme.
