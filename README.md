# futsal-tequilky.cz

Web ženského futsalového týmu **Tequilky Slavia Malé Hoštice** (1. futsalová liga žen).
Běží na <https://futsal-tequilky.cz>.

Je to jedna statická stránka: čisté HTML a CSS, kousek JavaScriptu přímo v `index.html`,
žádný build, žádné závislosti. Výsledky a tabulku si web během sezony doplňuje sám
(viz [Výsledky a tabulka](#výsledky-a-tabulka-automaticky)).

## Co je kde

| Soubor | K čemu je |
|---|---|
| `index.html` | Celý obsah webu: sekce Zápasy, Tabulka, O nás, Úspěchy, Reprezentace, Tým, Galerie, Nábor, Podpora, Kontakt |
| `styles.css` | Veškerý vzhled |
| `img/` | Znak (`crest.png`/`.webp`), fotka v úvodu (`team-hero.jpg`), galerie (`galerie/`) |
| `favicon.svg`, `apple-touch-icon.png` | Ikona v prohlížeči a na ploše telefonu |
| `CNAME` | Doména pro GitHub Pages (`futsal-tequilky.cz`). Nemazat |
| `data/season.json` | Rozpis zápasů sezony s výsledky; z něj se generuje rozpis na webu |
| `scripts/update_results.py` | Stahuje výsledky a tabulku z lz.futsalliga.cz |
| `.github/workflows/deploy.yml` | Nasazení webu a pravidelná aktualizace výsledků |

Složky `data/`, `scripts/` a `.github/` ani tohle README se na web nenahrávají.

## Jak udělat změnu

1. Uprav `index.html` nebo `styles.css`.
2. Podívej se na to lokálně:

   ```bash
   python3 -m http.server 8000
   ```

   a otevři <http://localhost:8000>.
3. Commitni a pushni do `main`. GitHub Actions web do minuty nasadí.

Průběh nasazení je v záložce **Actions** na GitHubu (workflow „Deploy to GitHub Pages“).
Workflow jde spustit i ručně: Actions → Deploy to GitHub Pages → Run workflow, nebo

```bash
gh workflow run "Deploy to GitHub Pages" --repo rstix/tequilky-landing
```

Ruční spuštění nejdřív stáhne nejnovější výsledky a pak web nasadí.

GitHub Pages posílá soubory s desetiminutovou cache. Aby prohlížeč nespojil nové HTML se
starým stylem, nasazení přidá k odkazu na `styles.css` verzi podle commitu
(`styles.css?v=1a2b3c4d`). V repu odkaz zůstává obyčejný `styles.css`.

### Časté úpravy

- **Hráčky a realizační tým**: sekce `id="tym"`. Každá hráčka je jedna `<li class="player">`.
  Odznaky: `badge--rep` R = reprezentantka, `badge--role` B = brankářka, T = hrající trenérka.
  Při přidání nebo odebrání hráčky oprav i počet v nadpisu (`subhead__count`).
- **Fotky do galerie**: velká verze do `img/galerie/NN.jpg` (delší strana max. 1600 px),
  náhled do `img/galerie/NN-n.jpg` (šířka 720 px). Na Macu:

  ```bash
  sips -Z 1600 fotka.jpg --out img/galerie/29.jpg
  ```

  ```bash
  sips --resampleWidth 720 img/galerie/29.jpg --out img/galerie/29-n.jpg
  ```

  Pak přidej `<li>` do `<ul class="gallery">` podle ostatních (i s `width`/`height`
  náhledu a popisem v `alt`). Prvních 13 fotek je vidět hned, zbytek pod tlačítkem.
- **Rozpis zápasů**: na webu je vidět 4 zápasy kolem dneška (poslední odehraný a další),
  zbytek je pod tlačítkem. Počet je `SHOW` ve skriptu na konci `index.html`.
  Zápasy samotné se neupravují v `index.html`, ale v `data/season.json` (viz níže).

## Výsledky a tabulka (automaticky)

Během sezony se skóre zápasů a ligová tabulka doplňují samy, nikdo nemusí nic přepisovat.

**Odkud.** Z webu ligy <https://lz.futsalliga.cz>: rozpis a výsledky z
[`/matches/2027`](https://lz.futsalliga.cz/matches/2027), tabulka ze
[`/standings/2027`](https://lz.futsalliga.cz/standings/2027) (2027 = sezona 2026/27).
Je to veřejná stránka bez ochrany proti robotům. fotbal.cz se automaticky nečte: je za
ochranou Cloudflare a jeho podmínky převzetí obsahu bez souhlasu FAČR zakazují. Odkazy
„Detail“ u zápasů na fotbal.cz ale vedou dál.

**Kdy.** Workflow se spouští samo v neděli ve 22:00 a v pondělí v 7:00 a v 19:00
(středoevropský čas; v `deploy.yml` je to v UTC). Zápasy se hrají o víkendu a liga výsledky
zveřejní nejpozději v pondělí.

**Co se stane při běhu.**

1. Job `results` spustí `python3 scripts/update_results.py`. Skript:
   - stáhne rozpis a najde všech 22 zápasů Tequilek; ke každému zápasu v
     `data/season.json` (páruje se podle dvojice domácí–hosté) doplní skóre, halu a
     případně nový termín, pokud liga zápas přesunula;
   - stáhne tabulku; dokud liga žádnou nezveřejní, zůstává na webu abecední nulová tabulka;
   - z `data/season.json` znovu vygeneruje rozpis v `index.html` (mezi
     `<ol class="fixtures" id="fixtures">` a `</ol>`) a tělo tabulky (`<tbody>` v
     `<table class="standings">`), k tabulce napíše „Aktualizováno <datum> podle
     futsalliga.cz“ a po prvním výsledku změní v úvodu „Sezona začíná“ na „Sezona začala“.
2. Když se něco změnilo, bot `github-actions[bot]` to commitne
   („results: update from futsalliga.cz“) a job `deploy` web hned nasadí.
   Když se nic nezměnilo, plánovaný běh skončí bez nasazení.

Na webu pak u odehraného zápasu svítí skóre (výhra červeně, prohra černě, remíza šedě)
a v popisku „výhra“ / „prohra“ / „remíza“.

**Když se něco pokazí.** Pokud lz.futsalliga.cz nejde, změní vzhled stránky nebo vrátí
nesmyslná data (jiný počet týmů v tabulce, zápas, který v našem rozpisu není), skript
nic nepřepíše, skončí chybou a GitHub pošle majiteli repa e-mail o neúspěšném běhu.
Web zůstane v posledním dobrém stavu.

Lokálně se dá skript pustit kdykoli (jen standardní Python 3.9+, nic se neinstaluje):

```bash
python3 scripts/update_results.py
```

Napíše buď `updated: …`, nebo `nothing new: …`. Druhé spuštění po sobě nikdy nic nezmění.

### Ruční zásahy

- **Neupravuj rozpis přímo v `index.html`.** Příští běh ho přegeneruje ze
  `data/season.json` a ruční úprava zmizí. Úpravy dělej v `data/season.json` a pak
  spusť skript (nebo ruční workflow), který je propíše do stránky.
- **Výsledek dřív, než ho má liga**: zapiš ho do `data/season.json` jako
  `"score": [domácí, hosté]`, např. `[3, 1]`. Skript ho nechá, dokud liga nezveřejní svůj,
  pak použije ten ligový.
- **Odložený zápas**: `"postponed": true` přidá k zápasu „odloženo“. Nový termín doplní
  skript sám, jakmile ho liga zveřejní.
- **Jiné jméno týmu**: liga občas píše názvy jinak (např. „SK Rapid Ústí n. L.“). Převod na
  názvy z našeho rozpisu je ve slovníku `NAMES` na začátku skriptu.

### Nová sezona

Jednou ročně, po vylosování nové sezony:

1. Nový `data/season.json`: 22 zápasů Tequilek s `round`, `kickoff`, `home`, `away`,
   `fotbal` (odkaz na detail zápasu), `venue: null`, `score: null`, `postponed: false`.
   Pole `season` a `source` nahoře.
2. Ve skriptu `SEASON = "2028"` (číslo je rok, kdy sezona končí) a seznam týmů v
   `NAMES`, pokud přibyly nové zkratky.
3. V `index.html` nadpis „Sezona 2026/27“, text „Sezona začíná …“, abecední nulová
   tabulka nových 12 týmů a odkazy na fotbal.cz (kalendář, celý rozpis, tabulka).
4. Pustit skript lokálně, zkontrolovat výsledek v prohlížeči, pushnout.

## Hosting a doména

- **Web**: GitHub Pages z tohoto repa (`rstix/tequilky-landing`), nasazuje GitHub Actions.
  HTTPS certifikát vydává GitHub sám.
- **Doména a DNS**: Forpsi (admin.forpsi.com). Čtyři A záznamy na GitHub Pages
  (`185.199.108.153`, `.109.153`, `.110.153`, `.111.153`) a `www` jako CNAME na
  `rstix.github.io`. Ostatní záznamy (MX, SPF, DKIM, DMARC, SRV, autoconfig) patří
  týmovému e-mailu, nemazat. DNSSEC je zapnutý: měnit záznamy, ne nameservery.
- **E-mail** `info@futsal-tequilky.cz` běží u Forpsi.
- „Hosting“ SuperSite Easy u Forpsi je jen stavebnice webu bez FTP; tenhle web na něm neběží.

## Kontaktní formulář

Formulář v sekci Kontakt posílá zprávy přes službu [FormSubmit](https://formsubmit.co)
na `info@futsal-tequilky.cz`. Je aktivovaný (aktivace proběhla potvrzovacím e-mailem na
tu adresu). Při změně adresy se musí nová adresa znovu aktivovat: první zpráva na ni
přijde jako žádost o potvrzení.

Ochrana proti spamu je neviditelná, návštěvník nic neodklikává:

- adresa endpointu se skládá až v JavaScriptu, takže ji roboti v HTML nenajdou;
- formulář odeslaný dřív než 3 s po načtení stránky se zahodí;
- skryté pole `_honey`, které vyplní jen robot;
- `_blacklist` s typickými spamovými slovy.

Robot dostane stejné „Děkujeme, zpráva byla odeslána.“ jako člověk, jen se nic neodešle.
Bez JavaScriptu formulář nahradí odkaz na e-mail.
