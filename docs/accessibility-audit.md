# Erişilebilirlik denetimi

Tarih: 2026-11-01. Hedef: WCAG 2.2 AA.

Bu dosya denetimin kaydıdır. "Özet" başlığından sonrası ilk denetimi anlatır ve değiştirilmedi.

## Düzeltme sonrası

Tarih: 2026-11-01. Denetim düzeltmelerden sonraki kodla, aynı araçlarla yeniden çalıştırıldı: Playwright 1.64.1, axe-core 4.14.0, Chrome, aynı axe etiketleri. Canlı akış yerel sahte API ile ölçüldü. Gerçek NVDA ile test yapılmadı.

### axe sonucu

20 taramada 0 ihlal. Tarananlar açık tema, koyu tema, zorunlu renkler ve azaltılmış harekette başlangıç, Gelişmiş açık, deneme teklifi, alan hatası ve canlı Onayla durumlarıdır. Koyu temada `color-contrast` için gelen "emin değilim" notları ilk denetimdeki yanlış alarmdır: axe zemini beyaz sanıyor, ekrandan okunan zemin `rgb(18, 18, 18)`. Yeni öğelerin gerçek oranı açık temada 21:1, koyu temada 18,73:1.

### Bulguların durumu

- A1 kapandı. Onayla'dan sonra odak metin kutusunda. Teklif süresi Onayla odaktayken dolduğunda da aynı.
- A2 kapandı. Esc sonrası odak metin kutusunda, dil değişiminde aynı düğmede. Canlı takipte durum değişince liste 0 kez yeniden çizildi.
- A3 kapandı. Canlı modda sayfada deneme metni yok, Alt+H gerçek para uyarısıyla başlıyor.
- B1 kapandı. Esc başka alandayken metni silmiyor, metin kutusundayken siliyor.
- B2 kapandı. Canlı mod ve mikrofon metin olarak ve çift çerçeveyle belli.
- B3 kapandı. `tr-TR` Türkçe, `en-US` ve `de-DE` İngilizce açılıyor. Dil seçimi Gelişmiş dışında.
- B4 kapandı. Dil değişimi iki dilde de duyuruluyor.
- B5 açık. Olası sorun, yalnızca NVDA gösterebilir. Odak metin kutusuna geçiyor ve 129 karakterlik açıklama teklifle yarışabilir.
- D1 kapandı. Bekleme halinde kesik çerçeve ve bekleme imleci var.
- D2 kapandı. Kısayollar görünür.
- D3 kapandı. Odak çerçevesi açık temada 7,5:1, koyu temada 8,97:1. Zorunlu renklerde sistem rengi kullanılıyor.
- D4 kapandı. İki seçenekte de `lang` var.
- D5 kısmen açık. `noscript` notu var, ama JavaScript kapalıyken etiketler ve 2 düğme boş kalıyor.
- D6 kapandı. Hatalı alan `aria-invalid` alıyor, odak oraya gidiyor, yazınca işaret kalkıyor. Miktar, iki token alanı ve metin kutusu denendi.
- D7 kapandı. `maxlength` kaldırıldı, uzun cümle sunucudan okunuyor.
- D8 büyük ölçüde kapandı. Sayfa başlığı ve etiket aralığı düzeltildi. Süre uyarısı eklendi: deneme ve canlıda 30 saniye kala bir kez, süre dolunca bir kez duyuruluyor, cevap verilince iptal oluyor. Duyuru sırası (iki duyuru 100 milisaniye içinde gelirse biri kaybolur) açık.

### Yeni sorunlar

Yüksek ya da orta önemli yeni sorun çıkmadı.

- Y1, düşük, açık: Kısayollar artık hem görünür hem `aria-describedby` ile bağlı. Gözden geçirme kipinde NVDA aynı metni iki kez okuyabilir. NVDA ile doğrulanmalı.

### Değişmeyenler

Sekme sırası görsel sırayla aynı, yeni dil seçimi Gönder'den sonra geliyor. 320 ve 640 piksel genişlikte yatay kaydırma yok. Metin aralığında kesilen öğe yok. En küçük hedef 544x27 piksel. Alt+R çalışıyor. Sayfa hatası yok.

Bu rapor uygunluk belgesi değildir. NVDA, gerçek kontrast teması, Firefox, Edge ve mobil test edilmedi.

## Özet

- axe taraması 17 durumda 0 ihlal buldu.
- Elle yapılan testler 3 yüksek, 5 orta ve 8 düşük önemli sorun buldu.
- Sayfa bugün AA uyumlu sayılamaz. A2 ve A1 odak sırası kuralını (2.4.3, A düzeyi), D4 ise bölüm dili kuralını (3.1.2, AA düzeyi) ihlal ediyor.
- Önce düzeltilmesi gereken üçü: A1, A2 ve A3. Üçü de `main`'deki canlı takas akışını doğrudan etkiliyor.
- Yazma alanı, etiketler, kontrast, yeniden akış ve hareket testlerinin çoğu geçti. Ayrıntı aşağıda.
- Gerçek NVDA ile test yapılmadı. Bu raporun en büyük boşluğu budur.

## Satır numaraları

Kod iki yerde denetlendi ve iki yerde de aynı sonucu verdi:

- `main`, commit `a6117c8`. Geçici bir kopyadan 8002 portunda çalıştırıldı. `main` dosyalarına dokunulmadı.
- `deploy-prep`, kendi worktree'si, 8001 portunda.

`web/index.html` iki dalda aynıdır. `web/app.js` farklıdır. Bu yüzden her bulguda iki satır numarası var. `main` değiştikçe numaralar kayabilir, o yüzden her bulguda kod da adıyla geçiyor.

## Kullanılan yöntem

- Playwright 1.64.1, axe-core 4.14.0, Chrome 156.
- Sunucu: `python -m uvicorn app.main:app`, API anahtarı olmadan.
- axe etiketleri: wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa, best-practice.
- axe durumları: açık tema, koyu tema, zorunlu renkler ve azaltılmış hareket. Her birinde başlangıç, Gelişmiş açık, teklif görünür ve Onayla düğmesi görünür. Buna gerçek 1Click teklifi ile bir durum daha eklendi.
- Teklif ve canlı takip durumlarının çoğu sahte API yanıtıyla üretildi. Gerçek bir canlı takas çalıştırılmadı.
- `aria-live` sırası, sonuç alanındaki her değişiklik kaydedilerek ölçüldü. Bu, ekran okuyucunun ne okuduğunu değil, ona ne verildiğini gösterir.

## axe sonucu

0 ihlal. Koyu temada 4 durumda `color-contrast` "emin değilim" dedi ve 1:1 oran bildirdi. Bu yanlış alarm. axe arka planı beyaz sandı. Ekrandan okunan gerçek zemin `rgb(18, 18, 18)`, gerçek oran 18,73:1.

## Yüksek önem

### A1. Onayla düğmesinden sonra klavye odağı kayboluyor

- WCAG: 2.4.3 Odak Sırası (A).
- Dosya: `web/app.js`, `send` fonksiyonu. `main` satır 241 ve 246, `deploy-prep` satır 203 ve 208.
- Kanıt: Canlı modda Onayla düğmesine Enter ile basıldı. Yanıttan sonra düğme gizlendi ve odak `body` öğesine düştü.
- Etki: Bu, gerçek paranın onaylandığı andır. NVDA kullanıcısı yerini kaybeder. Sonraki Tab sayfanın başından başlar.
- Düzeltme: Düğmeyi gizlemeden önce odakta olup olmadığına bak. Odaktaysa metin kutusuna taşı.

```js
const confirmButton = byId("confirm");
const confirmHadFocus = document.activeElement === confirmButton;
confirmButton.hidden = !data.confirm_button;
// ...
if (pending || (confirmHadFocus && confirmButton.hidden)) sentence.focus();
```

### A2. Kimlik listesi yeniden çizilince odak kayboluyor

- WCAG: 2.4.3 Odak Sırası (A).
- Dosya: `web/app.js`, `renderIds` içindeki `list.replaceChildren()`. `main` satır 131, `deploy-prep` satır 123.
- Kanıt: Odak bir Kopyala düğmesindeyken üç durumda da odak `body` öğesine düştü:
  - Esc ile teklif iptal edildi. README'nin 8. adımı tam olarak bunu yaptırıyor.
  - Dil değiştirildi.
  - Yalnızca `main`: canlı takip yeni bir duruma geçti. `followSwap` her durum değişiminde listeyi yeniden çiziyor, yani kullanıcı hiçbir şey yapmasa da odak kayboluyor.
- Etki: `applyLanguage` da `renderIds` çağırdığı için her yanıt listeyi siler ve yeniden kurar.
- Düzeltme: Liste değişmediyse yeniden çizme. Değiştiyse odaktaki düğmenin anahtarını sakla ve yeni düğmeye geri ver. Bölüm gizlendiyse odağı metin kutusuna taşı.

```js
const focusedKey = document.activeElement.closest?.("#ids button")?.dataset.key;
// ... listeyi çiz, her düğmeye button.dataset.key = key yaz ...
if (focusedKey) {
  const next = list.querySelector(`button[data-key="${focusedKey}"]`);
  (next || sentence).focus();
}
```

### A3. Canlı mod açıkken sayfa "Para hareket etmez" diyor (yalnızca `main`)

- WCAG: Doğrudan bir başarı ölçütü değil. 3.3.4 Hata Önleme (Finansal) kuralının amacına aykırı.
- Dosya: `web/app.js`, `intro` satır 5 ve 49, `submit` satır 14 ve 58. `app/messages.py`, `help` metni satır 122 ve 230. Satırlar `main` içindir. `deploy-prep` canlı işlem yapmadığı için orada bu cümle doğrudur.
- Kanıt: Canlı mod açıldı (`aria-pressed` true). Sayfa girişi hâlâ `Para hareket etmez`, düğme hâlâ `Deneme teklifi al`. Yardım metni de `Şimdilik yalnızca deneme modu var, para hareket etmez` diyor.
- Etki: Ekran okuyucu kullanıcısı gerçek para riski varken tersini duyar. Bu projenin en temel sözünü bozar.
- Düzeltme: `setLiveMode` içinde giriş metnini ve düğme adını `liveMode` değerine göre değiştir. `intro` ve `submit` için ikişer metin tut. Yardım metnini de iki moda göre ayır.

## Orta önem

### B1. Esc başka alandayken yazılan metni siliyor

- WCAG: 3.3.4 ile ilgili, doğrudan ihlal değil.
- Dosya: `web/app.js`, `cancel` içindeki `sentence.value = ""`. `main` satır 341, `deploy-prep` satır 302.
- Kanıt: Metin kutusuna yazıldı, odak Miktar alanına geçti, Esc'e basıldı. Metin silindi ve `İptal edilecek bir işlem yok` duyuruldu.
- Etki: Yazılan cümle uyarısız kaybolur. README, NVDA'nın Esc'i ilk basışta odak modundan çıkmak için kullanabileceğini de not ediyor.
- Düzeltme: Yalnızca odak metin kutusundaysa temizle.

```js
if (document.activeElement === sentence) sentence.value = "";
```

### B2. Canlı mod ve mikrofon düğmesinin açık hali görünmüyor

- WCAG: Ekran okuyucu için doğru (`aria-pressed`). Görerek kullananlar için durum bilgisi eksik.
- Dosya: `web/index.html`, stil bloğu, satır 7 ile 22 arası. Kural yok.
- Kanıt: `aria-pressed` true yapıldı. Renk, zemin, çerçeve, kalınlık ve imleç değerleri aynı kaldı.
- Etki: Az gören bir kullanıcı canlı modun açık olduğunu düğmeden anlayamaz. `main`'de bu gerçek para demektir.
- Düzeltme: Yalnızca renge dayanmayan bir işaret ekle. Zorunlu renk modunda da çalışır.

```css
button[aria-pressed="true"] { border: 4px double currentColor; text-decoration: underline; }
```

### B3. Sayfa her zaman Türkçe açılıyor, dil seçimi Gelişmiş içinde

- WCAG: 3.1.1 geçiyor, çünkü `lang` doğru. Sorun kullanılabilirlikte.
- Dosya: `web/index.html` satır 2 ve 49 ile 53 arası. `web/app.js` `let language`, `main` satır 110, `deploy-prep` satır 102.
- Kanıt: `en-US` tarayıcıda sayfa `lang="tr"` ile açıldı ve etiket `Ne yapmak istiyorsun?` oldu.
- Etki: İngilizce konuşan bir ekran okuyucu kullanıcısı ya da hackathon hakemi dil seçimini bulmak için Türkçe bir bölümü açmak zorunda kalır. Sesli giriş de sayfa diline bağlı olduğu için yanlış dilde dinler.
- Düzeltme: Açılışta `navigator.language` değerine bak. Dil seçimini Gelişmiş dışına, sayfanın üstüne taşı.

### B4. Dil değişince hiçbir şey duyurulmuyor

- WCAG: 4.1.3 Durum Mesajları (AA) ile ilgili.
- Dosya: `web/app.js`, `langSelect` değişiklik dinleyicisi. `main` satır 396, `deploy-prep` satır 357.
- Kanıt: Dil `en` yapıldı. `html lang` değişti, sonuç alanına hiçbir şey yazılmadı.
- Etki: Tüm etiketler değişir ama ekran okuyucu kullanıcısı bunu duymaz.
- Düzeltme: Değişiklikten sonra yeni dilde kısa bir cümle duyur, örneğin `Dil İngilizce oldu` ya da `Language set to English`.

### B5. Odak metin kutusuna atlayınca uzun açıklama yanıtla yarışabilir

- Durum: Olası sorun. NVDA ile doğrulanmalı.
- WCAG: 4.1.3 ile ilgili.
- Dosya: `web/app.js`, `sentence.focus()`, `main` satır 246 ve 310, `deploy-prep` satır 208. `web/index.html` satır 30 ve 31.
- Kanıt: Formdan teklif alınınca odak metin kutusuna geçiyor. Kutunun `aria-describedby` metni 129 karakter. Hemen ardından yanıt duyuruluyor.
- Etki: NVDA önce etiketi ve kısayolları okuyabilir, teklifi geciktirebilir ya da kesebilir.
- Düzeltme: NVDA ile dene. Sorun varsa uzun açıklamayı kısalt ya da odak taşınmadan önce `aria-describedby` değerini geçici olarak kaldır.

## Düşük önem

### D1. Bekleme hali görünmüyor

- Dosya: `web/app.js`, `aria-disabled`, `main` satır 230, `deploy-prep` satır 192. Stil yok.
- Kanıt: `aria-disabled` true iken düğmenin görünümü aynı kaldı.
- Düzeltme: `button[aria-disabled="true"] { opacity: 0.7; cursor: progress; }`. Kontrastı yeniden ölç.

### D2. Kısayollar görerek kullananlardan gizli

- WCAG: 3.3.2 ile ilgili.
- Dosya: `web/index.html` satır 31.
- Kanıt: Kısayol metni `.visually-hidden` sınıfında. Az gören klavye kullanıcısı göremiyor.
- Düzeltme: Sınıfı kaldır ya da Gelişmiş'in yanında görünür bir yardım bağlantısı ekle.

### D3. Odak çerçevesi işletim sistemi rengine bağlı

- WCAG: 2.4.7 ve 1.4.11.
- Dosya: `web/index.html` satır 15.
- Kanıt: Bu makinede oran açık temada 4,50:1, koyu temada 3,49:1. İkisi de 3:1 sınırını geçiyor, ama koyu tema sınıra yakın. `Highlight` rengi sistemden sisteme değişir, başka bir sistemde sınırın altına düşebilir.
- Düzeltme: Açık ve koyu tema için sabit bir renk seç, `Highlight` yalnızca `@media (forced-colors: active)` içinde kalsın.

### D4. Dil seçeneklerinde `lang` yok

- WCAG: 3.1.2 Bölümlerin Dili (AA).
- Dosya: `web/index.html` satır 51 ve 52.
- Kanıt: İki seçeneğin de `lang` değeri yok. NVDA `English` kelimesini Türkçe sesle okuyabilir.
- Düzeltme: `<option value="tr" lang="tr">` ve `<option value="en" lang="en">`.

### D5. JavaScript yüklenmeden sayfa boş

- Dosya: `web/index.html` satır 26 ile 66 arası.
- Kanıt: JavaScript kapalıyken 5 düğmenin de adı boş, etiketler boş, açıklama yok.
- Düzeltme: Türkçe metinleri HTML'e doğrudan yaz. `<noscript>` ile bir açıklama ekle.

### D6. Alan hatalarında `aria-invalid` yok

- WCAG: 3.3.1 metin olarak geçiyor. Bu bir iyileştirme.
- Dosya: `web/index.html` satır 55 ile 62 arası, `web/app.js` `send`.
- Kanıt: Formda `aria-invalid` hiç kullanılmıyor. Hata yalnızca sonuç alanında söyleniyor.
- Düzeltme: Hata hangi alanla ilgiliyse o alana `aria-invalid="true"` ver ve odağı oraya taşı.

### D7. 300 karakter sınırı sessizce çalışıyor

- Dosya: `web/index.html` satır 30.
- Kanıt: `maxlength="300"` yazmayı uyarısız durdurur. Bu bulgu koddan okundu, ölçülmedi.
- Düzeltme: `maxlength` kaldır. Sunucudaki `too_long` mesajı zaten var ve ekran okuyucuya okunur.

### D8. Küçük görsel ve içerik notları

- Teklif süresi: 10 dakika bitmeden uyarı yok (`app/oneclick.py` satır 15, `QUOTE_TTL_MINUTES`). WCAG 2.2.1'de fiyat geçerliliği büyük olasılıkla "zorunlu" istisnasına girer, ama yavaş okuyan kullanıcı için son bir dakika uyarısı iyi olur.
- Sayfa başlığı: `nearagent` amacı söylemiyor (`web/index.html` satır 6, WCAG 2.4.2). Örnek: `nearagent: erişilebilir kripto asistanı`.
- Etiket aralığı: Odak çerçevesi metin kutusunun üstündeki etikete değiyor (`web/index.html` satır 10). `label` için `margin-bottom: 0.5rem` ekle.
- Duyuru yarışı (yalnızca `main`, koddan okundu): `announce` yeni çağrıda bekleyen duyuruyu iptal ediyor (`web/app.js` satır 121). Canlı takip sonucu ile Kopyalandı mesajı 100 milisaniye içinde gelirse biri hiç duyurulmaz. Sonuç `lastReply` içinde kaldığı için Alt+R ile okunur. Daha sağlamı küçük bir sıradır.

## Geçenler

- Sekme sırası: Metin kutusu, Mikrofon, Gönder, Onayla, Kopyala düğmeleri, Gelişmiş, Canlı mod, Dil, tokenler, Miktar, teklif düğmesi. Görsel sırayla aynı. Pozitif `tabindex` yok.
- Odak görünürlüğü: Test edilen 13 öğenin hepsinde açık temada, koyu temada ve zorunlu renklerde 3 piksel çerçeve var.
- Düğme ve alan adları: Hepsinin adı var. Kopyala düğmeleri hangi kimliği kopyaladığını söylüyor ve görünen `Kopyala` kelimesini içeriyor (2.5.3).
- `aria-live` sırası: Yavaş yanıtta sıra `Yanıt bekleniyor`, boşaltma, yanıt. Hızlı yanıtta yalnızca yanıt.
- Tekrar etmeme: Tüm akışlarda aynı metin üst üste yazılmadı. `main`'de canlı takip aynı durumu ikinci kez duyurmadı.
- Alt+R: Aynı yanıtı boşaltıp yeniden yazıyor. Üç hızlı basış tek okumaya iniyor.
- Beklerken Enter: İkinci istek gönderilmiyor.
- Beklerken Esc: `Bekleyen isteği iptal ettim` duyuruluyor.
- %200 yakınlaştırma: 640x400 görünümde yatay kaydırma yok.
- %400 yakınlaştırma (1.4.10): 320x256 görünümde yatay kaydırma yok, uzun kimlikler satır atlıyor.
- Metin aralığı (1.4.12): Kesilen öğe yok.
- Hedef boyutu (2.5.8): En küçük hedef 544x27 piksel, sınır 24 piksel.
- Renk kontrastı, açık tema: Metin 21:1, düğme metni 18,43:1, alan çerçevesi 4,54:1.
- Renk kontrastı, koyu tema: Metin 18,73:1, düğme metni 5,33:1, alan metni 11,2:1, alan çerçevesi 5,08:1.
- Yüksek kontrast: Zorunlu renk modunda düğmeler, alanlar, sonuç kutusu ve odak çerçevesi görünüyor. Ekran görüntüsü ile kontrol edildi.
- Hareket: CSS animasyonu, geçiş, kayan içerik, video ya da GIF yok. İstek sırasında çalışan animasyon sayısı 0.
- Kısayollar: Alt ile çalışıyor, tek tuş değil (2.1.4). AltGr için özel önlem var.
- Finansal onay (3.3.4): Canlı modda Enter tek başına onaylamıyor, teklif tekrar soruluyor.
- Sayfa yapısı: `main` bölgesi, tek `h1`, sıralı başlıklar, `html lang` dil değişince güncelleniyor.

## Doğrulanamayanlar

- Gerçek NVDA: Test edilmedi. Bir aracın sesi dinleyemediği için elle yapılmalı. README'deki `NVDA ile doğrulanacaklar` listesi hâlâ açık. B5 ve Esc davranışı oraya eklenmeli.
- Gerçek Windows kontrast teması: Chrome'un zorunlu renk taklidi kullanıldı, gerçek tema açılmadı.
- Gerçek tarayıcı yakınlaştırması: Küçük görünüm boyutuyla taklit edildi. Sonuç genelde aynıdır, ama elle bir kez denenmeli.
- Mikrofon: Test edilmedi.
- Firefox ve Edge: Yalnızca Chrome kullanıldı. Alt+H Firefox'ta Yardım menüsüyle çakışabilir.
- Dokunmatik ekran ve mobil ekran okuyucular: Test edilmedi.
- Otomatik araçlar WCAG sorunlarının yalnızca bir kısmını yakalar. Bu rapor uygunluk belgesi değildir.
