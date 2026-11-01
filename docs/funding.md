# Fonlama adımları

Bu adımlar gerçek para kullanır ve NEAR mainnet üzerinde çalışır. Hiçbiri henüz gerçek ağda denenmedi. İlk gerçek çağrı 7. adımdır.

## Özet

- Sahip adresine: 0,1 NEAR, NEAR ağında.
- Ajana: 5 USDC, Base ağında.
- Sıra: önce NEAR, en son USDC. USDC adresi ancak ajan kurulduktan sonra alınabilir.
- Ajan adresi tek kullanımlıktır. USDC'yi başka bir adrese ya da başka bir ağdan gönderme.

## Adımlar

Komutları proje klasöründe çalıştır. Claude Code içinden çalıştıracaksan başına `!` koy.

1. Partner anahtarını al: https://partners.near-intents.org. Anahtar `naa_` ile başlar ve bir kez gösterilir.
2. Anahtarı `.env` dosyasına kendin ekle: `NEAR_INTENTS_AGENT_API_KEY=...`. Sohbete yazma.
3. Sahip anahtarını üret. Ekrana yalnızca adres çıkar:

   ```
   node scripts/owner/generate_key.mjs
   ```

4. `.env` içindeki `OWNER_PRIVATE_KEY` satırını güvenli bir yere yedekle. Bu anahtar kaybolursa kurtarma yoktur.
5. Binance'ten sahip adresine 0,1 NEAR çek. Ağ olarak NEAR seç. Adres 64 karakterdir, tamamını kopyala. Binance en az tutar olarak daha fazlasını isterse onu gönder. Ücret, ekranda gösterilir.
6. Kuralları oku. Bu adım imza atmaz:

   ```
   .venv\Scripts\python scripts\owner_setup.py plan
   ```

   Ekranda onay kodu çıkar. Kod bir saat geçerlidir.
7. Ajanı oluştur. Bu ilk gerçek imzadır. `KOD` yerine onay kodunu yaz:

   ```
   .venv\Scripts\python scripts\owner_setup.py create --onay=KOD
   ```

   "Sahip hesabı aktif değil" derse NEAR henüz ulaşmamıştır. Biraz bekleyip aynı komutu yeniden çalıştır.
8. Yetkiyi ver. Aynı kodu kullan:

   ```
   .venv\Scripts\python scripts\owner_setup.py grant --onay=KOD
   ```

9. Yatırma adresini al:

   ```
   .venv\Scripts\python scripts\owner_setup.py deposit
   ```

   Ekranda ağ, adres, en az tutar ve son tarih çıkar. Komutu tekrar çalıştırmak aynı adresi verir. Yeni adres için `--yeni` ekle.
10. Binance'ten bu adrese 5 USDC çek. Ağ olarak **Base** seç. Binance ekranında Base yoksa çekme ve haber ver. Ücret düşüldükten sonra ulaşan tutar, 9. adımdaki en az tutardan az olmamalı.
11. Parayı kontrol et. Görünene kadar birkaç dakikada bir çalıştır:

    ```
    .venv\Scripts\python scripts\owner_setup.py balance
    ```

12. Acil durdurmayı dene. `unfreeze` önce kod verir, kodla çalıştırınca çözer. Çözme için 10 dakika bekleme süresi olabilir:

    ```
    .venv\Scripts\python scripts\owner_setup.py freeze
    .venv\Scripts\python scripts\owner_setup.py unfreeze
    .venv\Scripts\python scripts\owner_setup.py unfreeze --onay=KOD
    ```

13. Canlı modu aç: `.env` dosyasına `LIVE_ENABLED=true` ekle, uygulamayı yeniden başlat, Gelişmiş bölümünden `Canlı mod` düğmesine bas.
14. İlk gerçek işlem için geri dönüş adımlarına geç. Sınırlar: işlem başına 5 dolar, günde 10 dolar.

## Binance'e geri dönüş

Yol: USDC, ajanda NEAR'a çevrilir. NEAR sahip hesabına çekilir. Sahip hesabından Binance'e gönderilir.

Doküman, NEAR'ın sahip hesabına her zaman native NEAR olarak ulaştığını söylüyor. Bu yüzden unwrap adımı ve storage kaydı gerekmiyor. Hiçbir adım gerçek ağda denenmedi, ilk gerçek işlem senin onayınla yapılacak.

15. Canlı mod açıkken ajandaki bakiyeyi NEAR'a çevir. Tutarı bakiyeden biraz az yaz, çünkü işlem başına sınır 5 dolar:

    ```
    Base'deki 4,9 USDC'yi NEAR'a çevir
    ```

    Koşullar okunur. `evet` yaz ya da Onayla düğmesine bas. Enter onay sayılmaz.
16. Sonucu kontrol et, wNEAR görünmeli:

    ```
    .venv\Scripts\python scripts\owner_setup.py balance
    ```

17. NEAR'ı sahip hesabına çek. Sayfada `hepsini NEAR çek` yaz ya da terminalde şunu çalıştır:

    ```
    .venv\Scripts\python scripts\owner_setup.py withdraw --ne "hepsini NEAR"
    .venv\Scripts\python scripts\owner_setup.py withdraw --ne "hepsini NEAR" --onay=KOD
    ```

18. Binance'te Yatır ekranını aç, NEAR seç, ağ olarak NEAR Protocol seç, adresi kopyala.
19. **Binance memo ya da tag gösteriyorsa dur, gönderme.** NEAR transferinin memo alanı yoktur. Memosuz gönderim Binance'te kaybolabilir. Önce Binance desteğine sor.
20. Koşulları gör ve onay kodu al. Bu adım hiçbir şey göndermez:

    ```
    node scripts/owner/send_near.mjs --to ADRES --hepsi
    ```

    Betik sahip hesabında en az 0,05 NEAR bırakır. Belirli bir tutar için `--hepsi` yerine `--miktar 1,5` yaz.
21. Gönder. Kod tek kullanımlıktır, 10 dakika geçerlidir, o adres ve tutar içindir:

    ```
    node scripts/owner/send_near.mjs --to ADRES --hepsi --onay=KOD
    ```

    Ekrana işlem kimliği çıkar. Sonuç belirsiz derse yeniden gönderme, önce Binance'e ve bakiyeye bak.
22. Binance'te NEAR'ın geldiğini gör.

## Bu yolun sınırları

- Bütçe yeter ama pay az: 4,9 dolarlık takas ve 4,9 dolarlık çekim günlük 10 doların 9,8 dolarını kullanır. Aynı gün başka işlem yaparsan çekim ertesi güne kalır. `bugün çekilemez, yarın tekrar dene` denir.
- Çekimde tek işlem sınırı da geçerlidir. Bu sınır plan anındaki NEAR fiyatına göre yaklaşık 5 dolardır. Fiyat düştüyse `hepsini` sınıra iner, kalanı için yeni bir çekim gerekir.
- 0,1 USDC kadar bir artık ajanda kalabilir. Bu tutarı çevirmek için yeni bir takas gerekir.
- Çekim önizlemesi günde 20 ile sınırlıdır, her çekim 2 tane kullanır.
- Sayfadan çekim için canlı modun açık olması gerekir. Terminal çekimi canlı mod istemez.
- USDC'yi doğrudan sahip hesabına çekme. Bu token oradan Binance'e gönderilemez, kayıt gerekip gerekmediği de belgede yok. Uygulama bunu okurken uyarır.
- Binance'in NEAR yatırma için memo isteyip istemediğini ve en az tutarını doğrulayamadım. Doğru bilgi Binance ekranındadır.

## Sınırlar

- Binance ücretleri ve en az tutarları değişebilir. Doğru rakam Binance çekim ekranındadır.
- 0,1 NEAR, NEAR dokümanındaki örnek tutardır, zorunlu en az tutar değildir. Hesap ilk transferle oluşur.
- İşlem başına 5 dolar sınırı plan anındaki fiyatla token miktarına çevrilir. Günlük 10 dolar gerçek dolar sınırıdır.
- Teklif alanları ve işlem bağlantısı biçimi ilk gerçek işlemde kontrol edilmeli. Ayrıntı README'nin `Known limits` bölümünde.
