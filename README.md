# CHAPTER / — kurulum ve test

Ruh haline göre kitap öneren, kitabı içinde okutan ve okumayı alışkanlığa çeviren bir okuma uygulaması.

## İçindekiler

| Dosya | Ne işe yarar |
|---|---|
| `index.html` | Uygulamanın tamamı (HTML + CSS + JS tek dosyada) |
| `server.py` | Yerel sunucu: uygulamayı açar ve kitap API'lerine giden istekleri iletir |
| `ornek-kitaplar/` | Yükleme özelliğini denemek için PDF, EPUB ve TXT örnekleri |

## Çalıştırma (2 dakika)

1. Bilgisayarında **Python 3.8+** olduğundan emin ol (`python --version`).
2. Klasörde bir terminal aç ve önce kaynakları kontrol et:
   ```bash
   python server.py --check      # macOS/Linux: python3 server.py --check
   ```
   Her satırda `OK` görmelisin. `SSL certificate problem` yazarsa: `pip install certifi` çalıştır ve tekrar dene.
   `Gutenberg search` satırında **BUSY** görmen sorun değil: www.gutenberg.org bazı ağlara 503 döndürüyor. Uygulama o zaman aramayı **Gutendex** ve **Google Books** ile yapar; kitap dosyaları ve kapaklar Gutenberg'in resmi aynalarından (hangisi önce cevap verirse) indirilir ve `book-cache` klasöründe saklanır, böylece aynı kitap ikinci kez anında açılır.
3. Sunucuyu başlat:
   ```bash
   python server.py
   ```
4. Tarayıcıda aç: **http://localhost:8000**. Terminalde her kitap isteği `ok` ya da `x` ile ve nedeniyle listelenir.
5. Kapatmak için terminalde `Ctrl + C`.

> Port doluysa: PowerShell'de `$env:PORT=8080; python server.py`, macOS/Linux'ta `PORT=8080 python3 server.py`.
> Gutendex yanıt vermezse "Ücretsiz oku" sekmesi otomatik olarak Open Library'deki serbest (public domain) kitaplara geçer.

### Neden sunucu gerekiyor?
Tarayıcılar, bir sitenin başka bir siteden veri okumasına ancak o site izin verirse (CORS) izin verir. Kitap kaynaklarının bir kısmı bu izni göndermiyor. `server.py` bu istekleri senin bilgisayarından iletir; sadece şu adreslere izin verir: Open Library, Internet Archive, Gutendex / Project Gutenberg (ve resmi aynaları pglaf.org, nabasny.com), Vikikaynak. Başka hiçbir adrese istek göndermez (izin listesi dışı → 403).

`index.html`'i doğrudan çift tıklayarak da açabilirsin; her şey çalışır ama **Keşfet** bölümündeki canlı katalog büyük ihtimalle bağlanamaz.

## Hesaplar ve arkadaşlar (veritabanı)

`server.py` ile açtığında uygulama gerçek hesap sistemi kullanır:

- **Kayıt / giriş:** Şifreler düz metin olarak saklanmaz, PBKDF2 ile hash'lenir. Giriş yapınca tarayıcıya güvenli bir oturum çerezi (HttpOnly) verilir. 5 hatalı denemeden sonra o e-posta 5 dakika kilitlenir.
- **Veritabanı:** Klasörde `chapter.db` (SQLite) oluşur. Her kullanıcının kütüphanesi, ilerlemesi ve haftalık okuması kendi satırında durur, kimse başkasının verisini değiştiremez. Bu dosya tarayıcıdan indirilemez. Sıfırlamak için sunucuyu kapatıp dosyayı sil.
- **Birbirini görme:** Arkadaşlar bölümünde "CHAPTER'daki kişiler" listesi bu sunucuya kayıtlı herkesi gösterir. Birini eklediğinde arkadaşlık iki taraflı olur: birbirinizin Okuyor / Okumak istiyor / Bitirdi raflarını görürsünüz ve sohbet edebilirsiniz (mesajlar birkaç saniyede karşıya düşer).
- **Başka bir bilgisayardan giriş:** Aynı hesapla girince kütüphane ve kendi eklediğin kitaplar sunucudan gelir.
- **Kitap paylaşımı:** Yüklediğin ya da indirdiğin kitaplar sunucuya da kaydedilir. Arkadaşların rafında görünen kitaba tıklayınca kitap açılır, kütüphanelerine ekleyip okuyabilirler. Kitabı sadece sen, arkadaşların ve onu rafına eklemiş olanlar açabilir. Sadece paylaşma hakkın olan kitapları ekle.

### Sınıf arkadaşlarınla aynı anda denemek (aynı Wi-Fi)

```powershell
$env:HOST="0.0.0.0"; python server.py        # macOS/Linux: HOST=0.0.0.0 python3 server.py
```
Terminal, arkadaşlarının açacağı adresi yazar (ör. `http://192.168.1.23:8000`). Windows güvenlik duvarı izin isterse "Özel ağ" için izin ver. Okul ağları cihazlar arası bağlantıyı engelleyebilir; olmazsa telefondan hotspot açıp aynı ağa bağlanın.

### Google ile giriş (bir kerelik, ~3 dakika)

Giriş penceresindeki "Continue with Google" düğmesi, Google'dan bir **Client ID** alınca gerçek Google girişine dönüşür (Google'ın kendi düğmesi ve penceresi açılır). Client ID ücretsizdir:

1. https://console.cloud.google.com → yeni proje oluştur.
2. **APIs & Services → OAuth consent screen**: "External" seç, uygulama adı (CHAPTER) ve e-postanı yaz, kaydet. Test kullanıcısı olarak kendi Gmail adreslerinizi ekleyin.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID** → tür: **Web application**.
4. **Authorized JavaScript origins** kısmına ekle: `http://localhost` ve `http://localhost:8000` (sınıfla Wi-Fi üzerinden deneyecekseniz Google yerel IP adreslerine izin vermez; Google girişi için `localhost` kullanın).
5. Çıkan `xxxx.apps.googleusercontent.com` değerini proje klasöründeki **`google_client_id.txt`** dosyasına yapıştır ve `server.py`'yi yeniden başlat. Terminalde `Google sign-in: on` yazmalı.

Sunucu Google'dan gelen kimliği kendisi doğrular (hedef Client ID, e-posta doğrulaması, süresi). Client ID girilmemişse düğmeye basınca bu adımları anlatan kısa bir not çıkar.

### Sunucusuz mod

`index.html` doğrudan açıldığında ya da claude.ai'daki yayınlanmış sürümde veritabanı yoktur. Hesaplar o tarayıcıda kalır ama şifre yine hash'lenip kontrol edilir. Arkadaşlar sadece demo arkadaşlardır.

## Kitap kaynakları (API)

| Kaynak | Ne için | Not |
|---|---|---|
| **Google Books** API | Keşfet'teki ilk sekme: en geniş katalog, kapaklar, açıklamalar | Telifsiz kitaplar Gutenberg metniyle uygulamada açılır; diğerleri için "Önizle ↗" Google Books önizlemesini açar |
| **Project Gutenberg** (resmî OPDS arama kataloğu) | Telifsiz klasiklerin aranması ve **tam metni** (EPUB/TXT) | Arama doğrudan gutenberg.org'un kendi aramasıyla yapılır; ruh haline göre açılış listesi önceden seçilmiş klasiklerden anında gelir |
| **Open Library** Search API | Milyonlarca kitabın kataloğu, kapaklar | Okunabilir kitaplar en üstte. Telifli kitaplar Open Library'de **ücretsiz hesapla ücretsiz ödünç** alınır, uygulama içinde açılmaz |
| **Internet Archive** | Open Library'deki herkese açık taramaların metni | Gutenberg'de birebir aynı başlık yoksa OCR metni kullanılır |
| **Vikikaynak** (MediaWiki API) | Türkçe telifsiz eserler | |
| Gutendex | Yedek | Gutenberg araması yanıt vermezse devreye girer |
| Gutenberg aynası (aleph.pglaf.org) | Kitap dosyaları ve kapaklar | www.gutenberg.org meşgulse (HTTP 503) kitaplar Gutenberg'in kendi resmi aynasından indirilir |

### Google Books API anahtarı

Google Books anahtarsız da çalışır ama günlük arama sınırı düşüktür. Anahtar eklemek için:

1. [Google Cloud Console](https://console.cloud.google.com/) → Google ile giriş için kullandığın projeyi seç.
2. **APIs & Services → Library** → "Books API" → **Enable**.
3. **APIs & Services → Credentials → Create credentials → API key**. `AIza…` ile başlayan anahtarı kopyala. (İstersen **Restrict key → API restrictions → Books API** seç.)
4. Anahtarı bu klasördeki **`google_books_key.txt`** dosyasına tek satır olarak yapıştır ve `server.py`'yi yeniden başlat.

Not: `google_client_id.txt` içindeki `…apps.googleusercontent.com` değeri Google ile **giriş** içindir (OAuth Client ID); Google Books için ayrı bir **API key** gerekir. Anahtar tarayıcıya hiç gönderilmez: `server.py` onu Google Books isteklerine kendisi ekler. `python server.py --check` çıktısında `Google Books (key)` satırını görürsün.

Open Library, API kullanan uygulamaların kendini tanıtmasını istiyor. `server.py` içindeki `CONTACT` satırına kendi e-postanı yazabilirsin (ya da `CHAPTER_CONTACT=ad@ornek.com python3 server.py`). Sunucu Open Library'ye saniyede en fazla 1 istek gönderir.

## Test listesi

- [ ] Açılış: kitaplar uçuşuyor → **Open the book** → site açılıyor
- [ ] **03 Ruh hali**: 2'den fazla ruh hali seçilemiyor, sayı canlı güncelleniyor, kitap dili filtresi (EN/TR) çalışıyor
- [ ] **04 Your picks**: kitaplar Project Gutenberg'den rastgele gelir; ruh halini değiştir ya da **↻ Yeniden karıştır**'a bas → yeni liste
- [ ] Giriş yapmadan bir kitaba tıkla / kitap yükle → hesap açma penceresi açılmalı
- [ ] **05 Keşfet**: arama yap → "Ücretsiz oku · Gutenberg" sonucunda **Read now** → kitap indirilip okuyucuda açılıyor
- [ ] **05 Keşfet** → "Tüm katalog · Open Library" → ödünç alınabilir bir kitapta **Want to read** → kütüphanede görünüyor
- [ ] **05 Keşfet** → "Türkçe · Vikikaynak" → bir eser aç
- [ ] Raftaki **+ Add your own book** → `ornek-kitaplar/lighthouse.pdf` → önizleme → ekle → okuyucu
- [ ] **07 Bahçe**: sahneyi fareyle sürükle (etrafa bak), W A S D / ok tuşlarıyla yürü; telefonda sağ alttaki düğmeler. Gece temasında fenerler ve ateşböcekleri yanar
- [ ] Okurken birkaç kelime seç → renkli altını çiz ya da **✎ Not** ekle → not sayfanın üstünde post-it olarak çıkar; post-it'e veya **✎ Notlar** listesindeki bir öğeye tıklayınca o yere gidilir
- [ ] Okurken sayfa çevir → alttaki ilerleme ve **06 Alışkanlık / 07 Bahçe** kendiliğinden güncelleniyor
- [ ] Okuyucuda **✦ Recap** (Claude bağlı değilse çevrimdışı özet çalışır)
- [ ] Hesap oluştur → çıkış yap → yanlış şifreyle girmeyi dene (hata vermeli) → doğru şifreyle gir, kütüphane geri gelmeli
- [ ] İki farklı tarayıcıda (ör. Chrome + gizli pencere) iki hesap aç → **09 Arkadaşlar**’da "CHAPTER’daki kişiler"den birbirinizi ekleyin → rafları görün, sohbet edin
- [ ] Menü: **Friends** (okunmamış mesaj rozeti), **EN/TR**, açık/koyu tema, **Motion** (animasyonlar kapalıyken her şey yine çalışıyor)
- [ ] Üst menüde **Friends** → sağdan Instagram tarzı mesaj paneli açılır (kişi ekleme, CHAPTER'daki kişiler, sohbetler); bir kişiye tıkla → sohbet aynı yerde açılır, ← ile listeye dön
- [ ] İki hesap: biri diğerine mesaj atınca karşı tarafta üst menüde ve kişinin üstünde kırmızı sayı rozeti çıkmalı; sohbet açılınca kaybolmalı
- [ ] Giriş yapmışken sayfayı yenile → doğrudan **03 Mood**'dan başlamalı; yeni ziyaretçi **Prologue**'dan başlar
- [ ] İlk kez gelen ziyaretçi ve yeni açılan her hesap (e-posta ya da Google) Story'nin sonundan aşağı kaydırılamaz; **Find my book** düğmesi zıplayıp dikkat çeker, basınca devam edilir
- [ ] **02 Story** sonunda **Find my book** → hikâye kitabının sayfaları hızla döner, sayfaya yaklaşılır, “気分” başlığı çıkar ve sayfa çevrilerek 03 Mood açılır
- [ ] Telefonda rafta bir kitaba bir kez dokun → kitap öne gelir; tekrar dokun → kitabın sayfası açılır
- [ ] Birden fazla kitap okurken **06** bölümünde kapaklardan birini seç → “Okumaya devam et” o kitabı açar
- [ ] Giriş yapınca üst menüde 読 düğmesi: günlük okuma serin (bir sayfa çevirince bugün sayılır); basınca seri paneli açılır (son 14 gün, en uzun seri, bu hafta)
- [ ] Telefonda / tarayıcının mobil görünümünde aynı adımlar

## Bilinen sınırlar

- `server.py` olmadan açıldığında hesaplar sadece o tarayıcıda tutulur ve Google girişi demodur.
- Yapay zekâ özeti ve demo arkadaşların cevapları yalnızca claude.ai'da yayınlanan sürümde Claude ile çalışır; yerelde çevrimdışı yedek metinler kullanılır.
- Kitaplar tarayıcıda (IndexedDB) ve sunucuda saklanır; tarayıcı verisini silsen bile tekrar giriş yapınca sunucudan geri gelir.
- Taranmış (metni seçilemeyen) PDF'ler okunamaz; iki sütunlu PDF'lerde paragraf ayrımı kusurlu olabilir. En temiz sonuç EPUB/TXT ile alınır.
- "Bir ağaç ≈ 8.333 kâğıt yaprağı" yaygın bir kaba tahmindir.

## Klavye kısayolları

`B` kütüphane · `M` animasyon · `T` tema · `← →` okuyucuda sayfa · `Esc` kapat (ekranda gösterilmez, sadece kısayol)


## Telefona uygulama olarak kurmak (PWA)

CHAPTER / bir **PWA** (Progressive Web App): ayrı bir mobil uygulama yazmadan telefonda uygulama gibi açılır. Ana ekranda kendi simgesi olur, adres çubuğu olmadan tam ekran açılır ve son açılan sayfa internetsiz de görünür.

- **Android (Chrome):** siteyi aç → menü ⋮ → **Uygulamayı yükle** (ya da sitenin altındaki **Install the app** düğmesi).
- **iPhone (Safari):** siteyi aç → **Paylaş** → **Ana Ekrana Ekle**.

Önemli: telefonlar tam kurulum için **HTTPS** ister. Aynı Wi-Fi'de `http://192.168.x.x:8000` ile açınca iPhone yine ana ekrana ekler, Android ise kısayol oluşturur; çevrimdışı açılış ve "Uygulamayı yükle" penceresi için siteyi HTTPS ile yayınlayın (ör. Render, Railway, PythonAnywhere ya da test için `cloudflared tunnel --url http://localhost:8000`). Bilgisayarda `http://localhost:8000` zaten güvenli sayılır, orada her şey çalışır.

Dosyalar: `manifest.webmanifest` (ad, renkler, simgeler), `sw.js` (çevrimdışı kabuk), `icons/`.


## Hız ve tutarlılık (son güncelleme)

- **Your picks parça parça gelir:** her kaynak cevap verdiği anda kitapları eklenir; yavaş bir kaynak diğerlerini bekletmez (en fazla 9 sn).
- **Hatırlanan seçimler:** aynı ruh hali / tür / dil için son seçimler 30 dakika saklanır; uygulama yeniden açılınca anında görünür.
- **Sunucu önbelleği:** katalog cevapları (Gutendex, Google Books, Open Library, Vikikaynak) `book-cache/api/` klasöründe 12 saat tutulur.
- **Tek sayı:** "books match" sayısı, Your picks'te gördüğün kitap sayısının aynısıdır (koleksiyondaki eşleşmeler + canlı seçimler).
- **Büyüyen raf:** tek rafa sığmayan kütüphane "Okunuyor / Okumak istiyorum / Bitti" etiketli raflara bölünür; telefonda 2, bilgisayarda 3 raf görünür, gerisi "Tüm rafları göster" ile açılır.
