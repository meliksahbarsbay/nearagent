# Fonlama adımları

Bu adımlar gerçek para kullanır ve NEAR mainnet üzerinde çalışır. Hiçbiri henüz gerçek ağda denenmedi. İlk gerçek çağrı 7. adımdır.

## Özet

- Sahip adresine: 0,1 NEAR, NEAR ağında.
- Ajana: yaklaşık 10 USDC, Base ağında.
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
10. Binance'ten bu adrese yaklaşık 10 USDC çek. Ağ olarak **Base** seç. Binance ekranında Base yoksa çekme ve haber ver. Ücret düşüldükten sonra ulaşan tutar, 9. adımdaki en az tutardan az olmamalı.
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
14. İlk takası küçük yap, örneğin 1 USDC. Sınırlar: işlem başına 5 dolar, günde 10 dolar.

## Parayı geri çekme

Para yalnızca sahip adresine gider. Bu adres imzalanan politikadan okunur, başka adres kabul edilmez. Çekim gerçek para kullanır ve hiç denenmedi, ilk gerçek çekim senin onayınla yapılacak.

Sayfadan:

1. Gelişmiş bölümünden `Canlı mod` düğmesine bas.
2. `paramı cüzdanıma çek`, `hepsini USDC çek` ya da `2 USDC'yi cüzdanıma çek` yaz, Enter'a bas. Ne çekileceği, nereye gideceği ve bütçeden ne kadar düşeceği okunur.
3. `evet` yaz ya da Onayla düğmesine bas. Enter tek başına onay sayılmaz.

Terminalden, `LIVE_ENABLED` gerekmez:

```
.venv\Scripts\python scripts\owner_setup.py withdraw --ne "hepsini USDC"
.venv\Scripts\python scripts\owner_setup.py withdraw --ne "hepsini USDC" --onay=KOD
```

İlk komut hiçbir şey göndermez, ne çekileceğini ve onay kodunu gösterir. Kod o tutara özeldir. Tutar değişirse kod çalışmaz.

## Çekim sınırları

- Çekim günlük 10 dolarlık bütçeden düşer. Bütçe yetmezse `bugün çekilemez, yarın tekrar dene` denir.
- İşlem başına sınır çekimlere de uygulanır, yani yaklaşık 5 dolar. 10 USDC tek seferde çekilemez. `hepsini çek` sınıra iner ve bunu söyler, kalan için komutu yeniden çalıştırırsın.
- Aynı gün takas da yaptıysan bütçe erken biter, kalanı ertesi güne kalır.
- Önizleme hakkı günde 20. Her çekim 2 önizleme kullanır.
- Birden çok token varsa hangisini istediğini söylemen gerekir. Tek komut bütün tokenleri çekmez.
- Çekilen para NEAR ağındaki sahip hesabına gelir. Base USDC, NEAR üzerindeki USDC olarak gelir. Oradan Binance'e göndermek için bu projede bir komut yok. Sahip anahtarını bir NEAR cüzdanına aktarman gerekir.

## Sınırlar

- Binance ücretleri ve en az tutarları değişebilir. Doğru rakam Binance çekim ekranındadır.
- 0,1 NEAR, NEAR dokümanındaki örnek tutardır, zorunlu en az tutar değildir. Hesap ilk transferle oluşur.
- İşlem başına 5 dolar sınırı plan anındaki fiyatla token miktarına çevrilir. Günlük 10 dolar gerçek dolar sınırıdır.
- Teklif alanları ve işlem bağlantısı biçimi ilk gerçek işlemde kontrol edilmeli. Ayrıntı README'nin `Known limits` bölümünde.
