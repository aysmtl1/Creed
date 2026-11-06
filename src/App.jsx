import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Bean from "./components/Bean.jsx";

gsap.registerPlugin(ScrollTrigger);

const MENU = [
  { n: "Espresso", d: "Yoğun, tam gövdeli, kadife kremalı.", p: 85, tag: "Klasik" },
  { n: "Flat White", d: "İpeksi süt köpüğü, çift shot.", p: 115, tag: "Popüler" },
  { n: "Cold Brew", d: "18 saat soğuk demleme, ferah.", p: 120, tag: "Yaz Gözdesi" },
  { n: "Türk Kahvesi", d: "Közde, bol köpüklü, lokumla.", p: 95, tag: "Geleneksel" },
  { n: "Latte", d: "Yumuşak içim, vanilya seçeneğiyle.", p: 110, tag: "Favori" },
  { n: "San Sebastian", d: "Günlük taze, akışkan merkez.", p: 140, tag: "Tatlı" },
];

const STATS = [["12", "Çekirdek Çeşidi"], ["4800", "Aylık Fincan"], ["7", "Yıllık Tecrübe"]];

export default function App() {
  const root = useRef(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const ctx = gsap.context(() => {
      if (reduce) { gsap.set(".bean-layer", { display: "none" }); return; }

      // 1) Çekirdek kırılma animasyonu (Aynen korundu)
      const tl = gsap.timeline({
        scrollTrigger: { trigger: "#intro", start: "top top", end: "+=260%", scrub: 1, pin: true, anticipatePin: 1 },
      });
      gsap.set(".reveal", { opacity: 0, scale: 0.8, filter: "blur(14px)" });
      tl.to(".hint", { opacity: 0, duration: 0.2 }, 0)
        .to(".bean", { scale: 1.12, duration: 0.7, ease: "none" }, 0)
        .to(".bean", { keyframes: { x: [0, -7, 7, -9, 9, -4, 0], rotation: [0, -2, 2, -3, 3, -1, 0] }, duration: 0.7, ease: "none" }, 0)
        .to(".glow", { opacity: 1, scale: 1.5, duration: 0.6 }, 0.35)
        .to(".half-l", { xPercent: -140, yPercent: -65, rotation: -12, duration: 1.1, ease: "power2.in" }, 0.8)
        .to(".half-r", { xPercent: 140, yPercent: 65, rotation: 12, duration: 1.1, ease: "power2.in" }, 0.8)
        .to(".bean-bg", { opacity: 0, duration: 0.9 }, 1.0)
        .to(".reveal", { opacity: 1, scale: 1, filter: "blur(0px)", duration: 1, ease: "power2.out" }, 1.0)
        .to(".bean-layer", { opacity: 0, duration: 0.3 }, 1.8)
        .from(".hero-line", { y: 50, opacity: 0, stagger: 0.15, duration: 0.5 }, 1.5);

      // 2) Menü kartları sırayla gelir (wearedirect tarzı yumuşak fade-up + scale)
      gsap.set(".card", { opacity: 0, y: 80, scale: 0.95 });
      ScrollTrigger.batch(".card", {
        start: "top 85%",
        onEnter: (batch) => gsap.to(batch, { opacity: 1, y: 0, scale: 1, stagger: 0.1, duration: 0.8, ease: "power3.out", overwrite: true }),
      });

      // 3) Başlıklar için modern clip-path veya yukarı süzülme efekti
      gsap.utils.toArray(".sec-title").forEach((el) =>
        gsap.from(el, { y: 50, opacity: 0, duration: 1, ease: "power3.out", scrollTrigger: { trigger: el, start: "top 85%" } })
      );

      // 4) Parallax + sayaçlar
      gsap.to(".blob", { yPercent: -35, ease: "none", scrollTrigger: { trigger: "#about", scrub: true } });
      
      gsap.utils.toArray(".count").forEach((el) => {
        const o = { v: 0 };
        gsap.to(o, {
          v: +el.dataset.to, duration: 2, ease: "power1.out", snap: { v: 1 },
          onUpdate: () => (el.textContent = o.v),
          scrollTrigger: { trigger: el, start: "top 90%", once: true },
        });
      });

      // Ziyaret kutusu modern giriş efekti
      gsap.from(".visit-box", { y: 60, opacity: 0, duration: 1, ease: "power3.out", scrollTrigger: { trigger: "#visit", start: "top 80%" } });
    }, root);

    return () => ctx.revert();
  }, []);

  const skip = () => window.scrollTo({ top: window.innerHeight * 3.6, behavior: "smooth" });

  return (
    <div ref={root} className="selection:bg-latte selection:text-roast">
      {/* Header */}
      <header className="fixed left-0 right-0 z-50 flex items-center justify-between bg-roast/60 px-6 py-4 text-crema backdrop-blur-md transition-all" style={{ top: "env(safe-area-inset-top, 0px)" }}>
        <a href="#intro" className="serif text-xl font-extrabold tracking-wider">☕ Çekirdek</a>
        <nav className="flex gap-6 text-sm font-medium" aria-label="Ana menü">
          <a href="#menu" className="transition hover:text-latte">Menü</a>
          <a href="#about" className="transition hover:text-latte">Hakkımızda</a>
          <a href="#visit" className="transition hover:text-latte">Ziyaret</a>
        </nav>
      </header>

      {/* Giriş Bölümü (Değiştirilmedi) */}
      <section id="intro" className="relative h-screen w-full overflow-hidden">
        <div className="reveal absolute inset-0 z-0 flex flex-col items-center justify-center px-6 text-center" style={{ background: "radial-gradient(circle at 50% 40%, #8a5632 0%, #3b2314 70%)" }}>
          <p className="hero-line mb-3 text-sm uppercase tracking-[0.3em] text-latte">Günlük kavrulmuş · Elle demlenmiş</p>
          <h1 className="hero-line text-5xl font-extrabold leading-tight text-crema md:text-7xl">Kahve bir ritüeldir.</h1>
          <p className="hero-line mt-4 max-w-md text-crema/80">Her fincan, tek bir çekirdeğin hikâyesiyle başlar. Gel, yavaşla, tadını çıkar.</p>
          <a href="#menu" className="hero-line mt-8 rounded-full bg-latte px-8 py-3 font-semibold text-roast transition hover:scale-105 shadow-lg">Menüyü Keşfet</a>
        </div>

        <div className="bean-layer absolute inset-0 z-10">
          <div className="bean-bg absolute inset-0" />
          <div className="glow absolute left-1/2 top-1/2 h-[70vh] w-[70vh] -translate-x-1/2 -translate-y-1/2 opacity-0" />
          <div className="bean absolute inset-0 flex items-center justify-center">
            <div className="relative flex items-center justify-center" style={{ width: "min(56vh, 90vw)", height: "62vh" }}>
              <div className="absolute inset-0 flex items-center justify-center"><Bean side="l" /></div>
              <div className="absolute inset-0 flex items-center justify-center"><Bean side="r" /></div>
            </div>
          </div>
          <div className="hint absolute bottom-10 left-0 right-0 flex flex-col items-center gap-2 text-crema">
            <span className="text-sm tracking-widest uppercase font-light">Kaydır</span>
            <span className="animate-bounce text-2xl" aria-hidden="true">↓</span>
            <button onClick={skip} className="mt-1 rounded-full border border-crema/40 px-4 py-1 text-xs hover:bg-crema/10 transition">Girişi atla</button>
          </div>
        </div>
      </section>

      {/* Menü Bölümü (wearedirect tarzı modern grid kartlar) */}
      <section id="menu" className="mx-auto max-w-6xl px-6 py-32">
        <div className="text-center md:text-left mb-16">
          <span className="text-sm font-semibold tracking-widest uppercase text-latte mb-2 block">Özenle Seçildi</span>
          <h2 className="sec-title text-4xl font-extrabold md:text-5xl tracking-tight">Menümüz</h2>
          <p className="sec-title muted mt-2 text-lg">Seçili çekirdekler, özenle hazırlanmış benzersiz içecekler.</p>
        </div>

        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {MENU.map((m) => (
            <article key={m.n} className="card themed-card group relative overflow-hidden rounded-3xl p-8 shadow-xl border border-crema/10 transition-all hover:-translate-y-2 hover:shadow-2xl bg-white/5 backdrop-blur-sm">
              <div className="absolute top-6 right-6 text-xs font-semibold px-3 py-1 rounded-full bg-latte/10 text-latte border border-latte/20">
                {m.tag}
              </div>
              <div className="cup mb-6 h-20 w-20 rounded-2xl bg-latte/20 flex items-center justify-center shadow-inner transition group-hover:rotate-6 group-hover:scale-105">
                <span className="text-3xl">☕</span>
              </div>
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="text-2xl font-bold tracking-tight">{m.n}</h3>
                <span className="text-latte font-bold text-lg">₺{m.p}</span>
              </div>
              <p className="muted text-sm leading-relaxed">{m.d}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Hakkımızda Bölümü (Parallax ve istatistik vurgusu) */}
      <section id="about" className="relative overflow-hidden py-32 my-12" style={{ background: "#3b2314", color: "#e8d3b5" }}>
        <div className="blob absolute -right-24 top-10 h-96 w-96 rounded-full opacity-30 blur-3xl pointer-events-none" style={{ background: "radial-gradient(circle,#c89b6a,transparent 70%)" }} />
        <div className="relative mx-auto max-w-5xl px-6">
          <span className="text-sm font-semibold tracking-widest uppercase text-latte mb-2 block">Hikâyemiz</span>
          <h2 className="sec-title mb-6 text-4xl font-extrabold md:text-5xl tracking-tight">Nitelikli Kahve Tutkusu</h2>
          <p className="sec-title max-w-2xl text-lg opacity-90 leading-relaxed">
            Küçük bir kavurma atölyesinden çıktık. Çekirdeklerimizi doğrudan üreticilerden alıyor, her sabah taze kavuruyor ve en iyi demleme teknikleriyle fincanınıza taşıyoruz.
          </p>
          
          <div className="mt-20 grid grid-cols-1 sm:grid-cols-3 gap-8 text-center border-t border-crema/10 pt-16">
            {STATS.map(([v, l]) => (
              <div key={l} className="p-6 rounded-2xl bg-black/20 backdrop-blur-sm border border-crema/5">
                <div className="serif text-5xl font-extrabold text-latte md:text-6xl tracking-tight">
                  <span className="count" data-to={v}>0</span>+
                </div>
                <div className="mt-2 text-sm uppercase tracking-wider opacity-80">{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Ziyaret & İletişim Bölümü */}
      <section id="visit" className="mx-auto max-w-4xl px-6 py-24">
        <div className="visit-box themed-card rounded-3xl p-12 text-center shadow-2xl border border-crema/10 bg-gradient-to-b from-white/5 to-transparent backdrop-blur-md">
          <span className="text-sm font-semibold tracking-widest uppercase text-latte mb-2 block">Sizi Bekliyoruz</span>
          <h2 className="mb-4 text-4xl font-extrabold tracking-tight">Bizi Ziyaret Et</h2>
          <p className="muted text-lg mb-8">Alsancak, İzmir · Her gün 08:00 – 23:00</p>
          <a href="mailto:merhaba@cekirdek.cafe" className="inline-block rounded-full bg-latte px-10 py-4 font-bold text-roast transition hover:scale-105 shadow-xl hover:shadow-latte/20">
            Masa Ayırt
          </a>
        </div>
        <p className="muted mt-16 text-center text-xs tracking-wider">© 2026 Çekirdek Kahve · Tasarım & Kodlama</p>
      </section>
    </div>
  );
}