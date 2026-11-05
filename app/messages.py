"""Short sentences for the screen reader, in Turkish and English.

Every error says what happened and what to do next, and never carries a code.
"""
import re
from datetime import datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.oneclick import QUOTE_TTL_MINUTES, chain_name

MAX_DECIMALS = 6
MIN_SIGNIFICANT = 4
MAX_SPOKEN_SYMBOL = 12
SMALLEST_FEE = Decimal("0.01")
SECONDS_BEFORE_MINUTES = 90
LARGEST_SPELLED = 10**12

# Only the words ignore case: with the flag on, "ı" would also match a plain "I".
TURKISH_HINT = re.compile(r"[çğıöşüÇĞİÖŞÜ]|(?i:\b(cevir|fiyat|nedir|yardim|merhaba|ne kadar)\b)")

# Turkish suffixes depend on how a ticker is pronounced, so only known ones get one.
TURKISH_ACCUSATIVE = {
    "SOL": "SOL'u",
    "USDC": "USDC'yi",
    "USDT": "USDT'yi",
    "ETH": "ETH'yi",
    "BTC": "BTC'yi",
}

MESSAGES = {
    "tr": {
        "no_agent": "Ajan cüzdanı kurulmadı. Kurulum bitince yeniden dene.",
        "withdraw_terms": "{mode} Çekilecek: {amount} {symbol}. Nereye: sahip adresin, {chain} ağı. {received} {fee} {budget} Teklif {ttl} dakika geçerli.",
        "withdraw_capped": "Hepsi tek seferde çekilemez, tek işlem sınırı bu kadar.",
        "withdraw_native": "wNEAR sahip hesabına native NEAR olarak ulaşır.",
        "withdraw_stays": "Dikkat, bu token sahip hesabında kalır ve oradan Binance'e gönderilemez. Binance'e dönecekse önce NEAR'a çevir.",
        "withdraw_received": "Ulaşacak: yaklaşık {amount} {symbol}.",
        "withdraw_received_unknown": "Ulaşacak tutar önizlemede yok.",
        "withdraw_budget": "Bu çekim günlük bütçenden yaklaşık {usd} dolar düşer, kalan {left} dolar olur.",
        "withdraw_budget_no_cap": "Bu çekim yaklaşık {usd} dolar, günlük bütçe sınırı yok.",
        "withdraw_done": "Çekim tamamlandı. {amount} {symbol} sahip adresine gitti.",
        "withdraw_done_proof": "Çekim tamamlandı. {amount} {symbol} sahip adresine gitti. Gezgin bağlantısı Kimlikler bölümünde.",
        "withdraw_done_proof_id": "Çekim tamamlandı. {amount} {symbol} sahip adresine gitti. Kayıt kimliği için kopyala düğmesini kullan.",
        "withdraw_needs_live": "Çekim gerçek para kullanır, işlem yapılmadı. Önce Gelişmiş bölümünden canlı modu aç.",
        "withdraw_no_budget": "Günlük bütçe yetmiyor, bugün çekilemez. Yarın tekrar dene.",
        "withdraw_over_limit": "Bu tutar tek işlem sınırını aşıyor, işlem yapılmadı. Daha küçük bir tutar söyle.",
        "withdraw_owner_only": "Yalnızca sahip adresine çekebilirim, başka adres kabul etmem. Adres söylemeden yeniden iste.",
        "withdraw_no_target": "Politikada tek bir sahip adresi yok, işlem yapılmadı. Politikayı kontrol et.",
        "withdraw_empty": "Ajanda çekilecek bakiye yok. Önce bakiyeni kontrol et.",
        "withdraw_no_token": "Ajanda bu token yok, işlem yapılmadı. Bakiyede olanlar: {tokens}.",
        "withdraw_which": "Hangisini çekeyim, işlem yapılmadı. Token ya da zincir adıyla yeniden söyle: {tokens}.",
        "withdraw_preview_limit": "Bugünkü önizleme hakkı doldu, işlem yapılmadı. Yarın tekrar dene.",
        "agent_read_failed": "Ajan bilgisi alınamadı. Biraz sonra yeniden dene.",
        "policy_not_ready": "Politika henüz yürürlükte değil. Biraz sonra yeniden sor.",
        "policy": "Politika: izinli işlemler {actions}. {assets} varlık izinli. {budget} {frozen}",
        "action_names": {"swap": "takas", "withdraw": "çekim", "transfer": "transfer"},
        "action_join": " ve ",
        "policy_budget": "Günlük bütçe {limit} dolar.",
        "policy_no_budget": "Günlük bütçe sınırı yok.",
        "policy_frozen": "Ajan şu an dondurulmuş.",
        "policy_active": "Ajan çalışır durumda.",
        "budget_left": "Günlük bütçenden {left} dolar kaldı. Sınır {limit} dolar.",
        "budget_none": "Günlük bütçe sınırı yok. Sınır koymak için politikayı güncellemek gerekir.",
        "owner_key_missing": "Sahip anahtarı bu bilgisayarda yok, imza atılamadı. Önce sahip kurulumunu tamamla.",
        "freeze_done": "Ajan donduruldu, hiçbir işlem yapamaz. Açmak için ajanı çöz de.",
        "unfreeze_done": "Ajan çözüldü, yeniden işlem yapabilir. Durdurmak için ajanı dondur de.",
        "already_frozen": "Ajan zaten dondurulmuş. Açmak için ajanı çöz de.",
        "already_unfrozen": "Ajan zaten çalışır durumda. Durdurmak için ajanı dondur de.",
        "control_failed": "İşlem tamamlanmadı, ajanın durumu değişmedi. Yeniden dene ya da terminaldeki sahip betiğini kullan.",
        "control_pending": "İstek gönderildi, ama sonuç henüz belli değil. Biraz sonra politikamı oku de.",
        "unfreeze_wait": "Ajan şimdi çözülemez, ağın bekleme süresi dolmadı. Yaklaşık {minutes} dakika sonra yeniden dene.",
        "unfreeze_plan": (
            "Ajanı çözmek için sahip anahtarıyla imza atacağım. "
            "Ajan yeniden işlem yapabilir hale gelir, politikası değişmez. "
            "Onaylamak için şu kodu yaz: {code}. Vazgeçmek için hayır de."
        ),
        "code_wrong": "Kod uymuyor. Kodu yeniden yaz ya da vazgeçmek için hayır de.",
        "code_locked": "Kod üç kez yanlış girildi, hiçbir şey imzalanmadı. Yeniden denemek için ajanı çöz de.",
        "mode_dry": "Deneme modu.",
        "mode_live": "Canlı mod, gerçek para.",
        "live_on": "Canlı mod açık, onayladığın takaslar gerçek para kullanır. Onay için evet yaz ya da Onayla düğmesine bas.",
        "live_off": "Canlı mod kapalı. Deneme modundasın, para hareket etmez.",
        "live_not_configured": "Canlı mod için ajan cüzdanı kurulmadı. Deneme modunda devam edebilirsin.",
        "live_needs_word": "Canlı modda Enter onay sayılmaz. Evet yaz ya da Onayla düğmesine bas.",
        "agent_frozen": "Ajan dondurulmuş, çözmek için ajanı çöz de.",
        "live_over_limit": "Bu işlem {usd} dolar, tek işlem sınırı {limit} dolar, işlem yapılmadı. Daha küçük bir miktar söyle.",
        "live_over_daily": "Günlük sınır aşılıyor, kalan {left} dolar, işlem yapılmadı. Daha küçük bir miktar söyle ya da yarın yeniden dene.",
        "live_no_price": "Bu işlemin dolar değeri okunamadı, işlem yapılmadı. Biraz sonra yeniden dene.",
        "live_no_balance": "Ajanın bakiyesi yetmiyor, işlem yapılmadı. Ajana para yatır ya da daha küçük bir miktar söyle.",
        "live_budget": "Ajanın politika sınırı aşılıyor, işlem yapılmadı. Daha küçük bir miktar söyle ya da yarın yeniden dene.",
        "live_busy": "Ajan başka bir işlemi bitiriyor, bu işlem gönderilmedi. Biraz sonra yeniden iste.",
        "live_refused": "Ajan bu işlemi reddetti, para hareket etmedi. İsteği değiştirip yeniden dene.",
        "live_no_route": "Şu an bu takas için yol bulunamadı, işlem yapılmadı. Biraz sonra yeniden dene ya da başka bir token dene.",
        "live_too_low": "Bu tutar takas için çok düşük, işlem yapılmadı. Daha yüksek bir miktar dene.",
        "live_quote_unreadable": "Teklif okunamadı, işlem yapılmadı. Biraz sonra yeniden dene.",
        "live_ledger_broken": "Günlük harcama kaydı okunamadı, işlem yapılmadı. Kayıt dosyası düzelene kadar canlı işlem başlamaz.",
        "live_unknown": "Sonuç belirsiz, para hareket etmiş olabilir. Yeniden gönderme, önce bakiyeni kontrol et.",
        "live_changed": "Teklif değişti, işlem yapılmadı. Yeni teklifi okuyorum.",
        "live_processing": "İşleniyor. Bitince söyleyeceğim.",
        "live_approval": "Sahip onayı bekleniyor. Onaylanınca devam edecek.",
        "live_uncertain": "Sonuç henüz kesinleşmedi. Yeniden gönderme, takip ediyorum.",
        "live_done": "Tamamlandı. {amount} {symbol} aldın.",
        "live_done_proof": "Tamamlandı. {amount} {symbol} aldın. Gezgin bağlantısı Kimlikler bölümünde.",
        "live_done_proof_id": "Tamamlandı. {amount} {symbol} aldın. Kayıt kimliği için kopyala düğmesini kullan.",
        "voice_confirm_swap": "{give} {symbol_in} verip en az {min_out} {symbol_out} alacaksın. Onaylamak için evet onaylıyorum de. Vazgeçmek için iptal de.",
        "voice_confirm_withdraw": "{amount} {symbol} sahip adresine çekilecek. Onaylamak için evet onaylıyorum de. Vazgeçmek için iptal de.",
        "voice_needs_phrase": "Sesli onay için yalnızca evet yetmez. Evet onaylıyorum de, ya da iptal de.",
        "voice_unclear": "Seni net duyamadım, onay saymadım. İptal ettim, işlem yapılmadı.",
        "voice_silence": "Onay duymadım, iptal ettim. İşlem yapılmadı.",
        "voice_not_heard": "Cevabını duyamadım. Evet ya da hayır de.",
        "live_refunded": "İade edildi. Para ajanın kendi bakiyesine döndü. Yeni bir teklif isteyebilirsin.",
        "live_refunded_part": "Kısmen tamamlandı. {amount} {symbol} aldın, kalan para ajanın kendi bakiyesine döndü. Bakiyeni kontrol et.",
        "live_failed": "Başarısız, para hareket etmedi. Yeni bir teklif isteyebilirsin.",
        "live_failed_unknown": "Başarısız, para hareket etmiş olabilir. Otomatik yeniden denemedim, önce bakiyeni kontrol et.",
        "live_review": "İşlem incelemeye düştü, para hareket etmiş olabilir. Yeniden gönderme, destekle iletişime geç.",
        "live_lost": "Bu işlemin takibi kayboldu, örneğin uygulama yeniden başladı. Yeniden gönderme, önce bakiyeni kontrol et.",
        "high_fee": "Dikkat, ücret yüzde beşi geçiyor.",
        "confirm_question_live": "Onaylıyor musun? Evet yaz ya da Onayla düğmesine bas.",
        "large_question_live": (
            "Yaklaşık {words} dolar mı dedin? Evet yaz ya da Onayla düğmesine bas. "
            "Değilse hayır yaz ya da Esc'e bas."
        ),
        "give_exact": "",
        "give_most": "en çok ",
        "get_about": "yaklaşık ",
        "get_exact": "tam ",
        "usd_note": "Söylediğin {usd} dolar güncel fiyatla çevrildi.",
        "refund_note": "Artan para iade edilir.",
        "price_usd": "{usd} dolar yaklaşık {amount} {symbol}.",
        "balance_empty": "Cüzdanın boş. Para yatırınca burada görünür.",
        "balance_intro": "Cüzdanında:",
        "balance_row": "{amount} {symbol}, yaklaşık {usd} dolar.",
        "balance_row_tiny": "{amount} {symbol}, 0,01 dolardan az.",
        "balance_row_no_price": "{amount} {symbol}, dolar karşılığı bilinmiyor.",
        "balance_total": "Toplam yaklaşık {usd} dolar.",
        "history_empty": "Henüz kayıtlı işlem yok. Bir teklifi onaylayınca burada görünür.",
        "history_broken": "İşlem geçmişi okunamadı. Geçmiş dosyası düzelene kadar yeniden dene.",
        "history_intro": "Son {count} işlem.",
        "history_row": "İşlem {number}: {date}, {mode}. {gave} {gave_symbol} verildi, {got} {got_symbol} alındı, {status}.",
        "history_date": "{day} {month}, saat {time}",
        "history_months": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
        "history_modes": {"dry": "deneme", "live": "canlı", "withdraw": "çekim"},
        "history_status": {
            "dry": "işlem yapılmadı",
            "processing": "işleniyor",
            "uncertain": "sonuç kesinleşmedi",
            "approval": "onay bekliyor",
            "done": "tamamlandı",
            "refunded": "iade edildi",
            "failed": "başarısız",
            "review": "incelemede",
            "refused": "gönderilmedi",
            "unknown": "sonuç belirsiz",
        },
        "quote": (
            "{mode} Veriyorsun: {give}{amount_in} {symbol_in}. "
            "Alıyorsun: {get}{amount_out} {symbol_out}. "
            "En az garanti: {min_out} {symbol_out}. {fee} "
            "{duration} Teklif {ttl} dakika geçerli."
        ),
        "duration": "Süre: yaklaşık {time}.",
        "duration_unknown": "Süre bilgisi yok.",
        "fee": "Ücret: yaklaşık {usd} dolar.",
        "fee_tiny": "Ücret: 0,01 dolardan az.",
        "fee_unknown": "Ücret bilgisi yok.",
        "seconds": "{count} saniye",
        "minutes": "{count} dakika",
        "confirm_question": "Onaylıyor musun? Evet de ya da Enter'a bas.",
        "large_question": (
            "Yaklaşık {words} dolar mı dedin? Evet de ya da Enter'a bas. "
            "Değilse hayır de ya da Esc'e bas."
        ),
        "confirmed_dry": "Deneme modu: işlem yapılmadı.",
        "cancelled": "İptal ettim, işlem yapılmadı. Yeni bir cümle yazabilirsin.",
        "not_understood": "Cevabını anlayamadım. Evet ya da hayır de.",
        "expired": "Teklifin süresi doldu. İsteğini yeniden yaz.",
        "missing_amount": "Ne kadar çevirmek istiyorsun?",
        "amount_again": "Miktarı anlayamadım. Rakamla yaz, örneğin 10. Vazgeçmek için hayır de.",
        "price": "{amount} {symbol} yaklaşık {usd} dolar.",
        "assumed": "{tokens} kullandım; başka zincir istersen söyle.",
        "assumed_join": " ve ",
        "help": (
            "Takas teklifi ve fiyat söyleyebilirim. Örnek: 2 NEAR'ı USDC'ye çevir, "
            "ya da 1 SOL kaç dolar. Deneme modundasın, para hareket etmez."
        ),
        "help_live": (
            "Takas teklifi ve fiyat söyleyebilirim. Örnek: 2 NEAR'ı USDC'ye çevir, "
            "ya da 1 SOL kaç dolar. Canlı mod açık, onayladığın takaslar gerçek para kullanır."
        ),
        "empty_text": "Cümle boş. Bir cümle yaz, örneğin 1 SOL kaç dolar.",
        "too_long": "Cümle çok uzun. Daha kısa yaz.",
        "no_parser": "Cümle çözümleme kapalı. Gelişmiş bölümündeki formu kullan.",
        "parser_failed": "Cümleni çözemedim. Yeniden yaz ya da gelişmiş bölümündeki formu kullan.",
        "invalid_amount": "Miktar geçersiz. Sıfırdan büyük bir sayı yaz, örneğin 1,5.",
        "missing_token": "Token adı eksik. Gönderilen ve alınan tokeni yaz.",
        "same_token": "Gönderilen ve alınan token aynı. Farklı bir token seç.",
        "unknown_token": "{symbol} tokenini bulamadım. Token adını kontrol edip yeniden yaz.",
        "unknown_token_long": "Bu tokeni bulamadım. Adres yerine token adını yaz.",
        "token_not_on_chain": "{symbol} {chain} zincirinde yok. Şu zincirlerden birini seç: {chains}.",
        "no_price": "{symbol} için fiyat bilgisi yok. Biraz sonra yeniden dene.",
        "quote_rejected": "Teklif alınamadı. Daha yüksek bir miktar ya da başka bir token dene.",
        "upstream": "Teklif servisine ulaşılamadı. Biraz sonra yeniden dene.",
    },
    "en": {
        "no_agent": "The agent wallet is not set up. Try again after setup.",
        "withdraw_terms": "{mode} Withdrawing: {amount} {symbol}. To: your owner address, on {chain}. {received} {fee} {budget} Quote valid for {ttl} minutes.",
        "withdraw_capped": "All of it cannot go at once, so this is the limit for one transaction.",
        "withdraw_native": "wNEAR arrives at the owner account as native NEAR.",
        "withdraw_stays": "Warning: this token stays on the owner account and cannot go on to Binance from there. To return it, swap to NEAR first.",
        "withdraw_received": "Arriving: about {amount} {symbol}.",
        "withdraw_received_unknown": "The preview does not show the amount arriving.",
        "withdraw_budget": "This takes about {usd} dollars from your daily budget, leaving {left} dollars.",
        "withdraw_budget_no_cap": "This is about {usd} dollars, and there is no daily budget cap.",
        "withdraw_done": "Withdrawal done. {amount} {symbol} went to your owner address.",
        "withdraw_done_proof": "Withdrawal done. {amount} {symbol} went to your owner address. The explorer link is in the Identifiers section.",
        "withdraw_done_proof_id": "Withdrawal done. {amount} {symbol} went to your owner address. Use the copy button for the record ID.",
        "withdraw_needs_live": "A withdrawal uses real money, so nothing was sent. Turn on live mode in the Advanced section first.",
        "withdraw_no_budget": "The daily budget is too low, so this cannot be withdrawn today. Try again tomorrow.",
        "withdraw_over_limit": "This is over the one transaction limit, so nothing was sent. Ask for a smaller amount.",
        "withdraw_owner_only": "I can only withdraw to the owner address, and no other. Ask again without an address.",
        "withdraw_no_target": "The policy has no single owner address, so nothing was sent. Check the policy.",
        "withdraw_empty": "The agent has no balance to withdraw. Check your balance first.",
        "withdraw_no_token": "The agent does not hold that token, so nothing was sent. It holds: {tokens}.",
        "withdraw_which": "Which one should I withdraw? Nothing was sent. Say it again with a token or chain name: {tokens}.",
        "withdraw_preview_limit": "Today's previews are used up, so nothing was sent. Try again tomorrow.",
        "agent_read_failed": "I could not read the agent. Try again shortly.",
        "policy_not_ready": "The policy is not in force yet. Ask again shortly.",
        "policy": "Policy: allowed actions are {actions}. {assets} assets are allowed. {budget} {frozen}",
        "action_names": {"swap": "swap", "withdraw": "withdraw", "transfer": "transfer"},
        "action_join": " and ",
        "policy_budget": "The daily budget is {limit} dollars.",
        "policy_no_budget": "There is no daily budget cap.",
        "policy_frozen": "The agent is frozen.",
        "policy_active": "The agent is active.",
        "budget_left": "You have {left} dollars left of your daily budget. The cap is {limit} dollars.",
        "budget_none": "There is no daily budget cap. Setting one needs a policy update.",
        "owner_key_missing": "The owner key is not on this computer, so nothing was signed. Finish the owner setup first.",
        "freeze_done": "The agent is frozen and can do nothing. To resume, say unfreeze the agent.",
        "unfreeze_done": "The agent is unfrozen and can act again. To stop it, say freeze the agent.",
        "already_frozen": "The agent is already frozen. To resume, say unfreeze the agent.",
        "already_unfrozen": "The agent is already active. To stop it, say freeze the agent.",
        "control_failed": "That did not complete, and the agent's state did not change. Try again or use the owner script in a terminal.",
        "control_pending": "The request was sent, but the result is not known yet. Shortly, say read my policy.",
        "unfreeze_wait": "The agent cannot be unfrozen yet, because the cooldown is still running. Try again in about {minutes} minutes.",
        "unfreeze_plan": (
            "To unfreeze the agent I will sign with the owner key. "
            "The agent can act again, and its policy does not change. "
            "To confirm, type this code: {code}. To stop, say no."
        ),
        "code_wrong": "That code does not match. Type it again, or say no to stop.",
        "code_locked": "The code was wrong three times, so nothing was signed. To try again, say unfreeze the agent.",
        "mode_dry": "Dry run.",
        "mode_live": "Live mode, real money.",
        "live_on": "Live mode is on, and swaps you confirm use real money. To confirm, type yes or press the Confirm button.",
        "live_off": "Live mode is off. You are in dry mode, so no funds move.",
        "live_not_configured": "The agent wallet for live mode is not set up. You can continue in dry mode.",
        "live_needs_word": "Enter does not confirm in live mode. Type yes or press the Confirm button.",
        "agent_frozen": "The agent is frozen. To resume, say unfreeze the agent.",
        "live_over_limit": "This swap is {usd} dollars and the limit is {limit} dollars, so nothing was sent. Ask for a smaller amount.",
        "live_over_daily": "This would pass the daily limit, with {left} dollars left, so nothing was sent. Ask for less, or try again tomorrow.",
        "live_no_price": "The dollar value could not be read, so nothing was sent. Try again shortly.",
        "live_no_balance": "The agent's balance is too low, so nothing was sent. Fund the agent or ask for a smaller amount.",
        "live_budget": "This passes the agent's policy limit, so nothing was sent. Ask for less, or try again tomorrow.",
        "live_busy": "The agent is finishing another swap, so this one was not sent. Ask again shortly.",
        "live_refused": "The agent refused this swap, so no funds moved. Change the request and try again.",
        "live_no_route": "There is no route for this swap right now, so nothing was sent. Try again shortly, or try another token.",
        "live_too_low": "This amount is too low to swap, so nothing was sent. Try a higher amount.",
        "live_quote_unreadable": "The quote could not be read, so nothing was sent. Try again shortly.",
        "live_ledger_broken": "The daily spending record could not be read, so nothing was sent. Live swaps stay off until that file is fixed.",
        "live_unknown": "The result is unknown, and funds may have moved. Do not send it again. Check your balance first.",
        "live_changed": "The quote changed, so nothing was sent. Here is the new quote.",
        "live_processing": "Processing. I will tell you when it is done.",
        "live_approval": "Waiting for the owner's approval. It continues once approved.",
        "live_uncertain": "The result is not final yet. Do not send it again. I am following it.",
        "live_done": "Done. You received {amount} {symbol}.",
        "live_done_proof": "Done. You received {amount} {symbol}. The explorer link is in the Identifiers section.",
        "live_done_proof_id": "Done. You received {amount} {symbol}. Use the copy button for the record ID.",
        "voice_confirm_swap": "You give {give} {symbol_in} and get at least {min_out} {symbol_out}. To confirm, say yes I confirm. To stop, say cancel.",
        "voice_confirm_withdraw": "{amount} {symbol} will be withdrawn to your owner address. To confirm, say yes I confirm. To stop, say cancel.",
        "voice_needs_phrase": "By voice, yes alone is not enough. Say yes I confirm, or say cancel.",
        "voice_unclear": "I did not hear you clearly, so I did not count a yes. I cancelled, and nothing was sent.",
        "voice_silence": "I heard no confirmation, so I cancelled. Nothing was sent.",
        "voice_not_heard": "I did not hear your answer. Say yes or no.",
        "live_refunded": "Refunded. The funds went back to the agent's own balance. You can ask for a new quote.",
        "live_refunded_part": "Partly done. You received {amount} {symbol}, and the rest went back to the agent's own balance. Check your balance.",
        "live_failed": "Failed, and no funds moved. You can ask for a new quote.",
        "live_failed_unknown": "Failed, and funds may have moved. I did not retry. Check your balance first.",
        "live_review": "This swap needs review, and funds may have moved. Do not send it again. Contact support.",
        "live_lost": "Tracking for this swap was lost, for example after a restart. Do not send it again. Check your balance first.",
        "high_fee": "Warning: the fee is above five percent.",
        "confirm_question_live": "Do you confirm? Type yes or press the Confirm button.",
        "large_question_live": (
            "Did you mean about {words} dollars? Type yes or press the Confirm button. "
            "If not, type no or press Escape."
        ),
        "give_exact": "",
        "give_most": "at most ",
        "get_about": "about ",
        "get_exact": "exactly ",
        "usd_note": "Your {usd} dollars were converted at the current price.",
        "refund_note": "Any excess is refunded.",
        "price_usd": "{usd} dollars is about {amount} {symbol}.",
        "balance_empty": "Your wallet is empty. Funds appear here once deposited.",
        "balance_intro": "In your wallet:",
        "balance_row": "{amount} {symbol}, about {usd} dollars.",
        "balance_row_tiny": "{amount} {symbol}, under 0.01 dollars.",
        "balance_row_no_price": "{amount} {symbol}, dollar value unknown.",
        "balance_total": "About {usd} dollars in total.",
        "history_empty": "There are no saved trades yet. They appear here once you confirm a quote.",
        "history_broken": "The trade history could not be read. Try again once that file is fixed.",
        "history_intro": "Last {count} trades.",
        "history_row": "Trade {number}: {date}, {mode}. Gave {gave} {gave_symbol}, received {got} {got_symbol}, {status}.",
        "history_date": "{month} {day} at {time}",
        "history_months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "history_modes": {"dry": "dry run", "live": "live", "withdraw": "withdrawal"},
        "history_status": {
            "dry": "nothing executed",
            "processing": "processing",
            "uncertain": "not final",
            "approval": "awaiting approval",
            "done": "done",
            "refunded": "refunded",
            "failed": "failed",
            "review": "under review",
            "refused": "not sent",
            "unknown": "result unknown",
        },
        "quote": (
            "{mode} You give: {give}{amount_in} {symbol_in}. "
            "You get: {get}{amount_out} {symbol_out}. "
            "Guaranteed minimum: {min_out} {symbol_out}. {fee} "
            "{duration} Quote valid for {ttl} minutes."
        ),
        "duration": "Time: about {time}.",
        "duration_unknown": "No time estimate.",
        "fee": "Fee: about {usd} dollars.",
        "fee_tiny": "Fee: under 0.01 dollars.",
        "fee_unknown": "No fee information.",
        "seconds": "{count} seconds",
        "minutes": "{count} minutes",
        "confirm_question": "Do you confirm? Say yes or press Enter.",
        "large_question": (
            "Did you mean about {words} dollars? Say yes or press Enter. "
            "If not, say no or press Escape."
        ),
        "confirmed_dry": "Dry run: nothing was executed.",
        "cancelled": "Cancelled, nothing was executed. You can type a new sentence.",
        "not_understood": "I did not understand your answer. Say yes or no.",
        "expired": "This quote has expired. Type your request again.",
        "missing_amount": "How much do you want to convert?",
        "amount_again": "I could not read the amount. Type a number, for example 10. Say no to stop.",
        "price": "{amount} {symbol} is about {usd} dollars.",
        "assumed": "I used {tokens}; tell me if you want another chain.",
        "assumed_join": " and ",
        "help": (
            "I can give swap quotes and prices. For example: swap 2 NEAR to USDC, "
            "or what is 1 SOL worth. You are in dry mode, so no funds move."
        ),
        "help_live": (
            "I can give swap quotes and prices. For example: swap 2 NEAR to USDC, "
            "or what is 1 SOL worth. Live mode is on, and swaps you confirm use real money."
        ),
        "empty_text": "The sentence is empty. Type one, for example what is 1 SOL worth.",
        "too_long": "That sentence is too long. Try a shorter one.",
        "no_parser": "Sentence parsing is off. Use the form in the advanced section.",
        "parser_failed": "I could not read that sentence. Rephrase it or use the form in the advanced section.",
        "invalid_amount": "Invalid amount. Enter a number above zero, for example 1.5.",
        "missing_token": "A token name is missing. Enter the token to send and the token to receive.",
        "same_token": "Both tokens are the same. Choose a different token.",
        "unknown_token": "I could not find the token {symbol}. Check the name and try again.",
        "unknown_token_long": "I could not find this token. Type its name, not an address.",
        "token_not_on_chain": "{symbol} is not on {chain}. Choose one of these chains: {chains}.",
        "no_price": "No price is available for {symbol}. Try again shortly.",
        "quote_rejected": "No quote available. Try a higher amount or another token.",
        "upstream": "The quote service is unreachable. Try again shortly.",
    },
}

ONES = {
    "tr": ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"],
    "en": ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
}
TENS = {
    "tr": ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"],
    "en": ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"],
}
TEENS = [
    "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
]
SCALES = {
    "tr": ((10**9, "milyar"), (10**6, "milyon"), (10**3, "bin")),
    "en": ((10**9, "billion"), (10**6, "million"), (10**3, "thousand")),
}


def spell_below_thousand(number: int, lang: str) -> str:
    hundreds, rest = divmod(number, 100)
    tens, ones = divmod(rest, 10)
    words = []
    if lang == "tr":
        if hundreds:
            words += ["yüz"] if hundreds == 1 else [ONES[lang][hundreds], "yüz"]
        words += [TENS[lang][tens], ONES[lang][ones]]
    else:
        if hundreds:
            words += [ONES[lang][hundreds], "hundred"]
        if tens == 1:
            words.append(TEENS[ones])
        elif tens and ones:
            words.append(f"{TENS[lang][tens]}-{ONES[lang][ones]}")
        else:
            words += [TENS[lang][tens], ONES[lang][ones]]
    return " ".join(word for word in words if word)


def spell_number(number: int, lang: str) -> str:
    """Write a whole number in words: 500 is "beş yüz" or "five hundred"."""
    if number == 0:
        return "sıfır" if lang == "tr" else "zero"
    if number >= LARGEST_SPELLED:
        return str(number)
    words = []
    for scale, name in SCALES[lang]:
        count, number = divmod(number, scale)
        if count:
            # Turkish says "bin", never "bir bin".
            is_plain_thousand = lang == "tr" and scale == 1000 and count == 1
            words.append(name if is_plain_thousand else f"{spell_below_thousand(count, lang)} {name}")
    if number:
        words.append(spell_below_thousand(number, lang))
    return " ".join(words)


def detect_language(text: str) -> str:
    """Rough guess, for replies sent before the parser has run."""
    return "tr" if TURKISH_HINT.search(text) else "en"


def format_amount(value: str, lang: str) -> str:
    """Trim to a speakable number. Turkish uses a decimal comma.

    Rounds down, so a guaranteed minimum is never read out higher than it is.
    """
    number = Decimal(value)
    # Small amounts keep four significant digits, or they round to the same number.
    places = max(MAX_DECIMALS, MIN_SIGNIFICANT - 1 - number.adjusted())
    trimmed = number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_DOWN).normalize()
    text = f"{trimmed:f}"
    return text.replace(".", ",") if lang == "tr" else text


def say(key: str, lang: str, **values) -> str:
    return MESSAGES[lang][key].format(**values)


def from_atomic(value: str, decimals: int) -> str:
    return f"{Decimal(value).scaleb(-decimals):f}"


def say_duration(seconds: int, lang: str) -> str:
    if seconds < SECONDS_BEFORE_MINUTES:
        return say("seconds", lang, count=seconds)
    return say("minutes", lang, count=round(seconds / 60))


def fee_usd(quote: dict, exact_out: bool = False) -> Decimal | None:
    """1Click reports no total fee, so this is the value lost between input and output.

    It covers fees and price difference together. Zero means no USD value was given.
    """
    value_in = Decimal(quote.get("amountInUsd") or 0)
    value_out = Decimal(quote.get("amountOutUsd") or 0)
    if value_in <= 0 or value_out <= 0:
        return None
    if exact_out and quote.get("minAmountIn") and quote.get("amountIn"):
        # amountIn carries a slippage buffer that is refunded, so it is not a cost.
        value_in *= Decimal(quote["minAmountIn"]) / Decimal(quote["amountIn"])
    return max(value_in - value_out, Decimal(0))


def say_fee(fee: Decimal | None, lang: str) -> str:
    if fee is None:
        return say("fee_unknown", lang)
    if fee < SMALLEST_FEE:
        return say("fee_tiny", lang)
    return say("fee", lang, usd=format_amount(str(fee.quantize(SMALLEST_FEE, ROUND_HALF_UP)), lang))


def say_time(seconds: int | None, lang: str) -> str:
    if seconds is None:
        return say("duration_unknown", lang)
    return say("duration", lang, time=say_duration(seconds, lang))


def say_live_status(view: dict, lang: str) -> str:
    """One plain sentence for each state a live swap can reach."""
    state = view["state"]
    values = {"amount": format_amount(view.get("amount") or "0", lang), "symbol": view.get("symbol")}
    if state == "done":
        key = "withdraw_done" if view.get("withdraw") else "live_done"
        if not view.get("proof"):
            return say(key, lang, **values)
        # An intent hash alone opens in no explorer, so it is not called a link.
        linked = any(item["value"].startswith("https://") for item in view.get("proofs") or [])
        return say(f"{key}_proof" if linked else f"{key}_proof_id", lang, **values)
    if state == "refunded":
        if view.get("amount"):
            return say("live_refunded_part", lang, **values)
        return say("live_refunded", lang)
    if state == "failed":
        return say("live_failed" if view.get("never_ran") else "live_failed_unknown", lang)
    return say(f"live_{state}", lang)


def say_quote(
    quote: dict,
    symbol_in: str,
    symbol_out: str,
    min_out: str,
    lang: str,
    live: bool = False,
    ttl: int = QUOTE_TTL_MINUTES,
    exact_out: bool = False,
) -> str:
    return say(
        "quote",
        lang,
        mode=say("mode_live" if live else "mode_dry", lang),
        give=say("give_most" if exact_out else "give_exact", lang),
        get=say("get_exact" if exact_out else "get_about", lang),
        amount_in=format_amount(quote["amountInFormatted"], lang),
        symbol_in=symbol_in,
        amount_out=format_amount(quote["amountOutFormatted"], lang),
        min_out=format_amount(min_out, lang),
        symbol_out=symbol_out,
        fee=say_fee(fee_usd(quote, exact_out), lang),
        duration=say_time(quote["timeEstimate"], lang),
        ttl=ttl,
    )


def format_usd(value: str, lang: str) -> str:
    """Cents, rounded down, so a remaining budget is never read out higher than it is."""
    return format_amount(str(Decimal(value).quantize(SMALLEST_FEE, ROUND_DOWN)), lang)


def say_policy(data: dict, lang: str) -> str:
    policy = data.get("policy")
    if not policy or data.get("status") != "APPLIED" or not data.get("provider_policy_synced"):
        return say("policy_not_ready", lang)
    names = MESSAGES[lang]["action_names"]
    actions = MESSAGES[lang]["action_join"].join(names.get(a, a) for a in policy["actions"])
    assets = policy["assets"]
    daily = (policy.get("budget") or {}).get("daily_usd")
    budget = (
        say("policy_budget", lang, limit=format_usd(daily, lang))
        if daily is not None
        else say("policy_no_budget", lang)
    )
    return say(
        "policy",
        lang,
        actions=actions,
        assets=len(assets) if isinstance(assets, list) else say_all_assets(lang),
        budget=budget,
        frozen=say("policy_frozen" if policy["frozen"] else "policy_active", lang),
    )


def say_all_assets(lang: str) -> str:
    return "Tüm" if lang == "tr" else "All"


def say_balances(data: dict, lang: str) -> str:
    """Token by token, with dollars. Empty rows are skipped."""
    rows = []
    total = Decimal(0)
    entries = [
        e for e in data.get("balances") or []
        if e.get("balance") is not None and Decimal(e["balance"]) > 0
    ]
    symbols = [e.get("symbol") for e in entries]
    for entry in entries:
        amount = Decimal(entry["balance"])
        symbol = entry.get("symbol")
        if symbols.count(symbol) > 1:
            symbol = f"{symbol} ({chain_name(entry.get('blockchain', ''))})"
        values = {"amount": format_amount(str(amount), lang), "symbol": symbol}
        price = entry.get("price")
        if price is None:
            rows.append(say("balance_row_no_price", lang, **values))
            continue
        usd = amount * Decimal(str(price))
        total += usd
        key = "balance_row_tiny" if usd < SMALLEST_FEE else "balance_row"
        rows.append(say(key, lang, usd=format_usd(str(usd), lang), **values))
    if not rows:
        return say("balance_empty", lang)
    parts = [say("balance_intro", lang), *rows]
    if len(rows) > 1 and total >= SMALLEST_FEE:
        parts.append(say("balance_total", lang, usd=format_usd(str(total), lang)))
    return " ".join(parts)


def say_date(moment: str, lang: str) -> str:
    local = datetime.fromisoformat(moment).astimezone()
    month = MESSAGES[lang]["history_months"][local.month - 1]
    return say("history_date", lang, day=local.day, month=month, time=local.strftime("%H:%M"))


def say_history(entries: list[dict], lang: str) -> str:
    if not entries:
        return say("history_empty", lang)
    table = MESSAGES[lang]
    rows = [
        say(
            "history_row",
            lang,
            number=number,
            date=say_date(entry["at"], lang),
            mode=table["history_modes"][entry["mode"]],
            gave=format_amount(entry["gave"], lang),
            gave_symbol=entry["gave_symbol"],
            got=format_amount(entry["got"], lang),
            got_symbol=entry["got_symbol"],
            status=table["history_status"].get(entry["status"], entry["status"]),
        )
        for number, entry in enumerate(entries, start=1)
    ]
    return " ".join([say("history_intro", lang, count=len(entries)), *rows])


def say_withdraw(order, lang: str, ttl: int) -> str:
    """The terms of a withdrawal. The address has a copy button and is never read aloud."""
    if order.received_text:
        amount = format_amount(order.received_text, lang)
        received = say("withdraw_received", lang, amount=amount, symbol=order.symbol)
    else:
        received = say("withdraw_received_unknown", lang)
    usd = format_usd(str(order.usd), lang)
    if order.left_usd is None:
        budget = say("withdraw_budget_no_cap", lang, usd=usd)
    else:
        budget = say("withdraw_budget", lang, usd=usd, left=format_usd(str(order.left_usd), lang))
    fee = Decimal(order.fee_usd) if order.fee_usd is not None else None
    terms = say(
        "withdraw_terms",
        lang,
        mode=say("mode_live", lang),
        amount=format_amount(order.amount_text, lang),
        symbol=order.symbol,
        chain=chain_name(order.chain),
        received=received,
        fee=say_fee(fee, lang),
        budget=budget,
        ttl=ttl,
    )
    note = say("withdraw_native" if order.symbol == "wNEAR" else "withdraw_stays", lang)
    terms = f"{terms} {note}"
    return f"{say('withdraw_capped', lang)} {terms}" if order.capped else terms


def say_usd_note(amount: str, lang: str) -> str:
    return say("usd_note", lang, usd=format_amount(amount, lang))


def say_price_usd(usd: Decimal, token: dict, lang: str) -> str:
    amount = usd / Decimal(str(token["price"]))
    return say(
        "price_usd",
        lang,
        usd=format_amount(str(usd), lang),
        amount=format_amount(f"{amount:f}", lang),
        symbol=token["symbol"],
    )


def say_budget(data: dict, lang: str) -> str:
    daily = ((data.get("usage") or {}).get("budget") or {}).get("daily") or {}
    if daily.get("limit_usd") is None:
        return say("budget_none", lang)
    return say(
        "budget_left",
        lang,
        left=format_usd(daily["remaining_usd"], lang),
        limit=format_usd(daily["limit_usd"], lang),
    )


def say_large(usd: Decimal, lang: str, live: bool = False) -> str:
    words = spell_number(int(usd.to_integral_value(ROUND_HALF_UP)), lang)
    return say("large_question_live" if live else "large_question", lang, words=words)


def say_price(amount: Decimal, token: dict, lang: str) -> str:
    usd = amount * Decimal(str(token["price"]))
    return say(
        "price",
        lang,
        amount=format_amount(str(amount), lang),
        symbol=token["symbol"],
        usd=format_amount(str(usd), lang),
    )


def describe_token(token: dict, lang: str) -> str:
    chain = chain_name(token["blockchain"])
    if lang == "tr":
        name = TURKISH_ACCUSATIVE.get(token["symbol"], f"{token['symbol']} tokenini")
        return f"{chain} üzerindeki {name}"
    return f"{token['symbol']} on {chain}"


def say_assumed(tokens: list[dict], lang: str) -> str:
    """Name the chains we picked. Empty when the user chose them all."""
    if not tokens:
        return ""
    joined = MESSAGES[lang]["assumed_join"].join(describe_token(t, lang) for t in tokens)
    return " " + say("assumed", lang, tokens=joined)


def say_error(code: str, lang: str, details: dict) -> str:
    """A pasted address is unreadable aloud, so it never goes into the sentence."""
    symbol = details.get("symbol", "")
    if code == "unknown_token" and not 0 < len(symbol) <= MAX_SPOKEN_SYMBOL:
        return say("unknown_token_long", lang)
    money = {k: format_usd(details[k], lang) for k in ("usd", "limit", "left") if k in details}
    return say(code, lang, **{**details, **money})
