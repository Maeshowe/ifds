# Kvantitatív Intraday Trading Rendszer — Stratégiai Felülvizsgálat (Matematikai Változat)

**Időszak**: 2026. március 13. – 2026. május 8. (60 kereskedési nap, N=378 ügylet)
**Verzió**: 1.0 (matematikai változat)
**Készült**: 2026. május 8.
**Célközönség**: kvantitatív kutatók, alkalmazott matematikusok, statisztikusok
**Státusz**: technikai döntéselőkészítő anyag — formális keretben

A jelen dokumentum a `2026-05-08-strategic-review-full.md` matematikai megfelelője; ugyanazokra a finding-okra ugyanaz az adat, **de** a megfogalmazás formális, és bizonyos kvalifikálatlan állítások (statisztikai erő, multiple comparison, expectancy) explicit formális keretbe kerülnek.

---

## Tartalom

1. Notáció és előzetes definíciók
2. A pipeline matematikai modellje (6 fázis operátorként)
3. A scoring funkcionál és a multiplier chain
4. Empirikus eredmények — statisztikai inferencia
5. Strukturális diagnózis — bias-variance, multiple comparison, Kelly expectancy
6. A 2026 áprilisi átalakítás mérlege (formális mátrixban)
7. Három stratégiai irány — döntéselméleti keret
8. Kockázatkezelés és sztochasztikus modellek
9. Függelékek (kvantitatív részletek)

---

# 1. Notáció és előzetes definíciók

## 1.1 Idő, indexek, alapváltozók

Legyen $t \in \mathcal{T}$ egy diszkrét kereskedési nap, $\mathcal{T} = \{1, 2, \ldots, T\}$ ahol $T = 60$. Minden napon $t$-ben a rendszer egy halmazt nyit:

$$\mathcal{P}_t \subseteq \mathcal{U}_t, \quad |\mathcal{P}_t| \in \{0, 1, \ldots, 5\}$$

ahol $\mathcal{U}_t$ az aznapi kvalifikált univerzum, $\mathcal{P}_t$ a ténylegesen nyitott pozíciók halmaza, és a maximum kardinalitás $K_{\max} = 5$ (a 2026 áprilisi átalakítás óta; korábban 8).

Egy ügylet $i$-re az alábbi változókat definiáljuk:

| Változó | Jelentés |
|---------|----------|
| $S_i \in [0, 142.5]$ | A kompozit pontszám az entry pillanatában |
| $E_i \in \mathbb{R}_+$ | Az entry ár |
| $X_i \in \mathbb{R}_+$ | Az exit ár |
| $Q_i \in \mathbb{N}$ | A pozíció-mennyiség (részvényszám) |
| $R_i = (X_i - E_i) Q_i$ | A realizált hozam dollárban |
| $r_i = (X_i - E_i)/E_i$ | A realizált hozam százalékban |
| $\tau_i \in \{T_1, T_2, \text{Trail}, \text{MOC}, \text{SL}, \text{LossExit}\}$ | Az exit típusa |
| $\Delta t_i$ | A holding period (időkülönbség entry és exit között) |
| $A_i$ | Az ATR (Average True Range) az entry pillanatában |

A teljes mintaadatok: $N = \sum_{t=1}^{T} |\mathcal{P}_t| = 378$.

## 1.2 Az adat-generáló folyamat feltevései

Modelljükként vegyük fel, hogy a piac ár-folyamata egy **lokálisan-Brown-féle** sztochasztikus folyamat:

$$dP_t = \mu_t P_t \, dt + \sigma_t P_t \, dW_t + dJ_t$$

ahol $\mu_t$ a drift (regime-függő), $\sigma_t$ a volatilitás, $W_t$ standard Brown-mozgás, és $J_t$ egy **Poisson jump folyamat** earnings-, makro-, news-eseményekre. Ez a feltevés **lazán igaz** (a heavy-tailed empirikus eloszlás miatt), de **első közelítésnek megfelelő**.

A kereskedési rendszer feltételezett edge-e azon múlik, hogy létezik-e olyan $S_i$ pontszám-funkcionál és $w^*$ súlyvektor, amelyre:

$$\mathbb{E}[r_i | S_i = s] \neq \mathbb{E}[r_i] \quad \text{valamely } s \text{-re}$$

azaz a pontszám **feltételes várakozási értéke** különbözik a feltétel nélküli várakozási értéktől. Ha a Pearson korrelációs együttható $\rho(S, r) = 0$, az **gyenge bizonyíték** a $H_0: \mathbb{E}[r | S] = \mathbb{E}[r]$ nullhipotézisre, **de nem zárja ki** a non-lineáris vagy nem-monoton kapcsolatot.

## 1.3 A költségmodell

Egy ügylet $i$ teljes súrlódási költsége:

$$C_i = c_{\text{comm}} + s_i E_i Q_i$$

ahol $c_{\text{comm}} = \$2{,}86$ az IBKR Pro tier átlagos commission (becsült), és $s_i$ a slippage százalékban. A 60 napi minta empirikus átlaga: $\bar{s} \approx 0{,}002$ (0,2%). A nettó hozam:

$$R_i^{\text{net}} = R_i - C_i$$

## 1.4 A null-hipotézis és az alpha definíciója

Definiáljuk a **realizált alpha-t** mint a benchmark-tól (S&P 500) független várt többlet:

$$\alpha_i := r_i - \beta r_{\text{SPY}, i}$$

ahol $\beta$ a portfolio piaci béta-ja (becsülve OLS regresszióval). A portfolio szintű:

$$\bar{\alpha} = \frac{1}{T} \sum_{t=1}^{T} \alpha_t$$

A null-hipotézis:

$$H_0: \bar{\alpha} = 0 \quad \text{vs.} \quad H_1: \bar{\alpha} > 0$$

A 60 napi empirikus érték: $\bar{\alpha} = -0{,}0054 \cdot$/nap, $\sigma_{\alpha} \approx 0{,}012$. A standard hiba: $\text{SE}(\bar{\alpha}) = \sigma_{\alpha}/\sqrt{T} \approx 0{,}00155$. A t-statisztika:

$$t = \bar{\alpha}/\text{SE}(\bar{\alpha}) \approx -3{,}48$$

Ez **kétoldali p-érték** $\approx 0{,}0009$. **A null-hipotézist elutasítjuk**, **de a megfigyelt irány a HIPOTÉZISTŐL ELLENTÉTES** (negatív alpha, statisztikailag szignifikáns).

---

# 2. A pipeline matematikai modellje (6 fázis operátorként)

A rendszer hat egymást követő operátorral modellezhető, mindegyik egy bemeneti halmazt vagy állapotot transzformál. Legyen $\mathcal{S}_t$ az aznapi piaci állapot ($\mathcal{F}_t$-mérhető):

$$\mathcal{S}_t = (\text{OHLCV}_t, \text{Options}_t, \text{Macro}_t, \text{News}_t)$$

## 2.1 Phase 0 — Diagnosztika ($f_0$)

$$f_0: \mathcal{S}_t \to \mathcal{D}_t = (\text{VIX}_t, \text{TNX}_t, \text{YC}_t, \text{API\_health}_t)$$

A diagnosztika operátor a makró-szintű mérőszámokat extraktálja. Output: egy `Macro` struktúra, amelyet a későbbi fázisok mind input-ként használnak.

## 2.2 Phase 1 — BMI rezsim-osztályozó ($f_1$)

A "Big Money Index" egy **percentilis-alapú statisztikai osztályozó**, amely a piaci grouped daily bars alapján számítja az 2σ feletti volume-spike arányát:

$$\text{BMI}_t = \frac{1}{|\mathcal{M}|} \sum_{j \in \mathcal{M}} \mathbb{1}[V_{j,t} > \mu_{V_j} + 2\sigma_{V_j}]$$

ahol $\mathcal{M}$ az S&P 500 univerzum, $V_{j,t}$ az aznapi forgalom, és $\mu_{V_j}, \sigma_{V_j}$ a 30 napi mozgóátlag és szórás.

A klasszifikáció:

$$\text{Regime}_t = \begin{cases} \text{GREEN} & \text{ha } \text{BMI}_t \leq 25 \\ \text{YELLOW} & \text{ha } 25 < \text{BMI}_t < 80 \\ \text{RED} & \text{ha } \text{BMI}_t \geq 80 \end{cases}$$

**Empirikus megfigyelés**: a 60 napi időszakban $\text{Regime}_t = \text{YELLOW}$ minden $t$-re; sem GREEN, sem RED állapot nem fordult elő. **Ez azt jelenti, hogy a BMI a vizsgált mintán nem differenciál** (degenerált változó), így a rendszer **gyakorlatilag mindig long stratégiával fut**.

A BMI Momentum Guard egy **autoregresszív feltétel**:

$$K_t = \begin{cases} 5 & \text{ha } \text{BMI}_{t-2} > \text{BMI}_{t-1} > \text{BMI}_t \\ 8 & \text{egyébként (régi szabály, most már } K_{\max}=5\text{)}\end{cases}$$

## 2.3 Phase 2 — Univerzum-építés ($f_2$)

Az operátor egy szűrőkészlettel csökkenti az alapsokaságot:

$$\mathcal{U}_t = \{j \in \mathcal{M} : \text{MarketCap}_j \geq 2 \times 10^9 \land \text{Price}_j \geq 5 \land \overline{V}_j \geq 5 \times 10^5 \land \text{HasOptions}_j \land \neg \text{NearEarnings}_j(7)\}$$

ahol a "NearEarnings" predikátum 7 naptári napos előretekintést használ. **Tipikus kardinalitás**: $|\mathcal{U}_t| \in [1400, 1500]$ a screener előtt, $\approx 250$ a 7 napos earnings exclusion után.

**Strukturális megfigyelés**: a 60 napi adat 3 dokumentált eseten azt mutatta, hogy a `NearEarnings` predikátum **nem teljesen robosztus**:
- DTE (2026-05-01): a fundamentális szolgáltató 4-quarter earnings-history 2 jó beat / 4 → a `<0,5` küszöb nem aktiválódott
- AGNC (2026-05-04): 10-Q SEC filing event, nem earnings release → a predikátum nem jelez
- BUD (2026-05-05): európai ADR earnings → a fundamentális szolgáltató earnings calendar-ja az ADR-en hiányos → a predikátum nem jelez

A predikátum **type II error rate-je** (false negative) a 7 napi időablakban tehát $\approx 3/N_{\text{events}} = 3/40 = 0{,}075$ (becsült).

## 2.4 Phase 3 — Szektor-rotáció ($f_3$)

A 11 alapszektor-ETF $\mathcal{E} = \{XLK, XLF, \ldots\}$ közül a relatív 5-napos teljesítmény alapján rangsorolunk:

$$\rho_e^{(5)} = \frac{P_e^{(t)} - P_e^{(t-5)}}{P_e^{(t-5)}}, \quad e \in \mathcal{E}$$

A **Leader/Laggard halmazok**:

$$\mathcal{L}_t = \text{top}_3(\rho_e^{(5)}), \quad \mathcal{G}_t = \text{bottom}_3(\rho_e^{(5)})$$

A pontszám-módosítás ticker $j$ szektorára $\sigma(j)$:

$$\Delta S_j^{\text{sect}} = \begin{cases} +15 & \text{ha } \sigma(j) \in \mathcal{L}_t \\ -20 & \text{ha } \sigma(j) \in \mathcal{G}_t \\ 0 & \text{egyébként} \end{cases}$$

A VETO szabály egy **logikai konjunkció**: ha a szektor 5-napos és 30-napos relatív teljesítménye is a bottom 3-ban, az egész szektor kiesik:

$$\text{Veto}(e) = \mathbb{1}[e \in \mathcal{G}_t^{(5)}] \cdot \mathbb{1}[e \in \mathcal{G}_t^{(30)}]$$

## 2.5 Phase 4 — Pontszám-funkcionál ($f_4$)

Ez a pipeline szíve. Egy ticker $j$ pontszáma:

$$S_j(t) = w^T \phi_j(t) + \sum_{e \in \mathcal{E}} \Delta S_j^{\text{sect}} \cdot \mathbb{1}[\sigma(j) = e]$$

ahol $w = (0{,}60, 0{,}30, 0{,}10)^T$ a 2026 áprilisi átalakítás óta, és $\phi_j(t) = (\phi_j^{\text{flow}}, \phi_j^{\text{tech}}, \phi_j^{\text{funda}})^T$ a feature vektor.

A flow pontszám részletes formája:

$$\phi_j^{\text{flow}}(t) = 50 + \sum_{k=1}^{7} b_k \cdot g_k(\text{flow}_{j,k}(t))$$

ahol $b_k \in \{+10, +15, +30, \ldots\}$ a bónusz-koefficiens és $g_k$ a küszöb-függvény (binarizáló vagy lineáris).

| $k$ | Komponens | Bonus $b_k$ | $g_k$ típus |
|-----|-----------|------------|-------------|
| 1 | RVOL | +30 | lineáris (0-30) |
| 2 | Dark Pool % | +15 | bináris (>40%, >60%) |
| 3 | PCR | +15 | bináris (low/high) |
| 4 | OTM Call | +10 | bináris (>15%) |
| 5 | Block Trade | +15 | lineáris (count) |
| 6 | Buy Pressure | +15 / -15 | bináris (VWAP felett/alatt) |
| 7 | Squat Bar | +10 | bináris |

A clipping threshold $S_{\text{cut}} = 95$: ha $S_j > 95$, a ticker **kizárul** a "túlzsúfolt trade" szabály alapján — **bár a 60 napi adatban a Q5 (95+) gyakran beengedett ügyletek vannak, ami azt jelzi, hogy a clipping nem konzisztensen érvényesül**.

A pontszám **EWMA simítása** 10 napi időablakkal:

$$\tilde{S}_j(t) = \alpha S_j(t) + (1-\alpha) \tilde{S}_j(t-1), \quad \alpha = 2/(10+1) \approx 0{,}182$$

## 2.6 Phase 5 — Gamma Exposure operátor ($f_5$)

A piacvezetők gamma-exponáltsága:

$$\text{GEX}_j(t) = \sum_{k \in \text{strikes}} \Gamma_k(t) \cdot \text{OI}_k(t) \cdot \text{spot}_j(t)^2 \cdot 0{,}01$$

ahol $\Gamma_k$ a gamma a $k$-adik strike-on, $\text{OI}_k$ az open interest. A klasszifikáció:

$$M_{\text{GEX}}(j) = \begin{cases} 1{,}0 & \text{ha } \text{GEX}_j > \theta_+ \\ 0{,}5 & \text{ha } \text{GEX}_j < \theta_- \\ 0{,}6 & \text{ha high-vol regime} \\ 0{,}75 & \text{egyébként (undetermined)} \end{cases}$$

**Empirikus megfigyelés**: a 60 napi adatban $\sim 93/100$ ticker az `undetermined` kategóriába esik, ami a $0{,}75 \times$ multiplier-t alkalmazza. **Ez azt jelenti, hogy a GEX-szorzó a vizsgált mintán nem differenciál**, hanem egy uniform 0,75-os tax-ot vet ki.

## 2.7 Phase 6 — Pozíció-méretezés ($f_6$)

A végső pozíció-méret (notional dollárban):

$$N_j = \frac{0{,}007 \cdot \text{Equity}}{|E_j - SL_j|} \cdot M_{\text{total}}(j)$$

ahol a kockázat 0,7% az account equity-jéből, és $|E_j - SL_j|$ a stop-loss távolság (1,5 ATR).

A multiplier chain:

$$M_{\text{total}}(j) = \text{clamp}(M_{\text{VIX}} \cdot M_{\text{GEX}}(j) \cdot M_{\text{target}}(j) \cdot M_{\text{contradiction}}(j), \; 0{,}25, \; 2{,}0)$$

Az egyes szorzók formái:

- $M_{\text{VIX}} = \max(1{,}0 - \rho_{\text{VIX}}(\text{VIX}_t - 20), 0{,}1)$ ahol $\rho_{\text{VIX}} = 0{,}02$ a decay-rate.
- $M_{\text{target}}(j) = \begin{cases} 0{,}60 & \text{ha } P_j > 1{,}50 \cdot T_j^{12m} \\ 0{,}85 & \text{ha } P_j > 1{,}20 \cdot T_j^{12m} \\ 1{,}0 & \text{egyébként} \end{cases}$
- $M_{\text{contradiction}}(j) = 0{,}80 \cdot \mathbb{1}[\bigvee_{c \in \mathcal{C}} \text{cond}_c(j)] + 1{,}0 \cdot \mathbb{1}[\neg \bigvee_{c \in \mathcal{C}} \text{cond}_c(j)]$

ahol $\mathcal{C}$ az ellenmondás-feltételek halmaza (4 OR-feltétel, lásd a portfolio menedzseri változatban).

---

# 3. A scoring funkcionál és a multiplier chain elemzése

## 3.1 A scoring kompozíció lineáris modellje

A kompozit pontszám $S_j(t) = w^T \phi_j(t)$ formában egy **lineáris funkcionál** a feature vektoron. Ez **erős feltevés** és érdemes kvalifikálni:

**Feltevés 1 (lineáris séma)**: a flow, tech, funda komponensek **lineárisan kombinálódnak** egyetlen scalarrá. Ez **nem ad teret** a komponensek **interakcióinak** (pl. "magas flow csak akkor jó signal, ha alacsony funda is")

**Feltevés 2 (idő-stacionaritás)**: a $w$ súlyvektor **konstans** időben. Ez a 2026 áprilisi átalakítás óta változatlan, **de a regime-függés** (Stagflation vs Goldilocks) **nincs kezelve**.

**Feltevés 3 (homogén feature-eloszlás)**: a $\phi_j(t)$ feature-eknek **azonos eloszlása** különböző tickerekre. **Ez nem áll**: a low-cap tickereken a flow score különböző karakterű, mint a large-cap tickereken (4. fejezet quintile elemzés is ezt mutatja).

## 3.2 A bias-variance tradeoff

A scoring kompozíció egy **becslő**: a "valódi várt hozam" $\mathbb{E}[r_j | \mathcal{F}_t]$ becslését adja. A becslő MSE-je:

$$\text{MSE}(\hat{r}) = \text{Bias}^2(\hat{r}) + \text{Var}(\hat{r}) + \sigma_{\epsilon}^2$$

**A jelenlegi 7-komponensű flow score variance-domináns**: a 7 al-komponens hozzáadódik egyetlen scalarba, ami **növeli a varianciat** anélkül, hogy a bias-t csökkentené (ha 5/7 al-komponens nem prediktív, az 5 random komponens noise-t ad).

A **Lasso-szerű regularizáció** (a 0 súly = az al-komponens kikapcsolása) **csökkenti a varianciat**, miközben a **bias** csak akkor növekszik, ha a kiiktatott al-komponens **valóban** prediktív lenne. A 4.4 fejezetben (a portfolio változatban a 4.4) bemutatott statisztikák szerint a 7 al-komponens közül **csak 2 (PCR, RVOL) szignifikáns pozitív**, **1 szignifikáns negatív (OTM call)**, a többi nem szignifikáns. **A 4 nem-prediktív komponens kiiktatása a bias-t valószínűleg nem növeli**, **de a varianciát jelentősen csökkenti**.

## 3.3 A multiplier chain mint geometriai szorzó

A multiplier chain egy **geometriai szorzó**:

$$M_{\text{total}} = \prod_{i=1}^{4} M_i, \quad M_i \in [0{,}25, 2{,}0]$$

Mivel $M_i \in [0{,}25, 2{,}0]$, az egyetlen $M_i = 0{,}25$ a teljes szorzatot $\leq 0{,}5$-re leviszi. **Ez a szorzó-rendszer asszimmetriája**: egy "extrém" szorzó (pl. $M_{\text{VIX}} = 0{,}1$ VIX > 50 esetén) képes a teljes pozíció-méretet kvázi-zéróra csökkenteni, de **nincs ekvivalens "extrém növelő" mechanizmus** — a clipping $\leq 2{,}0$ aszimmetrikusan korlátoz.

A multiplier chain **információs tartalma** a 60 napi adatban:
- $M_{\text{VIX}}$: 60/60 napon = 1,0 (mert VIX < 20 a teljes mintán)
- $M_{\text{GEX}}$: 280/378 ügyleten = 0,75 (undetermined)
- $M_{\text{target}}$: ritkán aktiválódik
- $M_{\text{contradiction}}$: 2026 májusi új komponens, kis n

**A 4 szorzó közül 1 egész mintán degenerált** ($M_{\text{VIX}} = 1{,}0$), **1 majdnem mindig azonos érték** ($M_{\text{GEX}} = 0{,}75$). **Az effektív differenciálás a $M_{\text{target}}$-en és $M_{\text{contradiction}}$-on múlik**, amelyek a vizsgált mintán **kis n-en aktiválnak**.

---

# 4. Empirikus eredmények — statisztikai inferencia

## 4.1 Pontszám-prediktivitás: hipotézistesztelés

**Null-hipotézis**: $H_0: \rho(S, R) = 0$, kétoldali alternatívával $H_1: \rho(S, R) \neq 0$.

A 378-ügyletes empirikus értékek:

| Mutató | Érték | t-stat | p-érték | 95% CI |
|--------|-------|--------|---------|--------|
| Pearson $\rho(S, R)$ | -0,0003 | -0,005 | 0,996 | [-0,099, +0,099] |
| Spearman $\rho_s(S, R)$ | -0,007 | -0,128 | 0,898 | [-0,107, +0,094] |
| Pearson $\rho(S, r)$ | +0,005 | 0,089 | 0,929 | [-0,094, +0,104] |

**A null-hipotézist NEM elutasítjuk**. **De ez nem az effekt hiányának bizonyítéka** — csak annak, hogy a 60 napi adat **nem elég erős** egy small effect ($|\rho| < 0{,}10$) detektálására.

A statisztikai erő-elemzés: $n = 378$ esetén, $\alpha = 0{,}05$ kétoldali küszöbnél, az 80% power-hez szükséges effektméret:

$$|\rho_{\min}| \approx \frac{z_{1-\alpha/2} + z_{0{,}80}}{\sqrt{n-3}} \approx \frac{1{,}96 + 0{,}84}{\sqrt{375}} \approx 0{,}144$$

**Tehát ha a valódi $\rho$ értéke $|\rho| > 0{,}144$**, az adatból 80%-os valószínűséggel detektáljuk. A megfigyelt $|\rho| < 0{,}01$ **erős bizonyíték** a $|\rho_{\text{true}}| < 0{,}10$ true value-ra.

**Stratégiai értelmezés**: ha a true Pearson $\rho \in [-0{,}10, +0{,}10]$, az olyan **gyenge edge-et** jelent, hogy a Sharpe ratio közelítőleg:

$$\text{SR} \approx \rho \cdot \frac{\sqrt{N_{\text{annual}}}}{\sigma_R/\bar{R}}$$

ahol $N_{\text{annual}} \approx 1500$ ügylet/év, és $\sigma_R/\bar{R}$ a Sharpe-arány-mintázat. Egy konzervatív becslés: **ha** $\rho_{\text{true}} = 0{,}10$, akkor a maximum elérhető Sharpe $\approx 0{,}5 - 0{,}8$, ami **közepes** edge — **de** az operatív súrlódással (15-17% éves drag) **kvázi-elnyelt**.

## 4.2 Quintile elemzés — két-mintás Kolmogorov-Smirnov teszt

A Q5 (top 76 ügylet) és Q1 (bottom 75 ügylet) hozam-eloszlásai közötti különbség:

$$D = \sup_x |F_{Q1}(x) - F_{Q5}(x)|$$

ahol $F$ az empirikus eloszlásfüggvény. Az eredmények:

- $\bar{R}_{Q1} = -\$1{,}72$, $\bar{R}_{Q5} = -\$8{,}91$
- $D = 0{,}092$, $p$-érték $\approx 0{,}43$ (KS teszt 75 vs 76 mintán)

**A KS-teszt nem találja szignifikáns különbséget** Q1 és Q5 között. **De a Q3** ($\bar{R} = -\$17{,}88$) **és Q2** ($\bar{R} = +\$11{,}57$) **közötti különbség**:

- $D = 0{,}219$, $p$-érték $\approx 0{,}042$

**A Q2-Q3 közötti különbség marginálisan szignifikáns**. Ez azt sugallja, hogy a "magas pontszám paradoxon" **nem-monoton kapcsolat** — a középső pontszám-tartomány teljesít legjobban, a két extrém (Q1 és Q5) gyengébben.

## 4.3 Flow al-komponens dekompozíció — multiple comparison korrekció

A 7 al-komponens × 2 statisztika (Pearson + Spearman) = **14 hipotézisteszt**. A Bonferroni-korrekció:

$$\alpha_{\text{Bonferroni}} = 0{,}05 / 14 \approx 0{,}00357$$

A 232-ügyletes mintán a kritikus Pearson küszöb:

$$|\rho_{\text{crit}}| = z_{1-\alpha_{\text{Bonferroni}}/2}/\sqrt{n-3} \approx 2{,}918/\sqrt{229} \approx 0{,}193$$

**A flow al-komponensek** Bonferroni-korrigált szignifikanciája:

| Komponens | Pearson r | $|r|$ vs 0,193 | Bonferroni-szig.? |
|-----------|-----------|-----------------|--------------------|
| **PCR** | +0,203 | $> 0{,}193$ | ✓ |
| **OTM call** | -0,194 | $> 0{,}193$ | ✓ (marginal) |
| RVOL | +0,147 | $< 0{,}193$ | ✗ |
| Block trade | -0,117 | $< 0{,}193$ | ✗ |
| Buy pressure | +0,068 | $< 0{,}193$ | ✗ |
| Squat bar | +0,036 | $< 0{,}193$ | ✗ |

**A multiple comparison korrekció után csak a PCR és az OTM call marad szignifikáns**. **Az RVOL** (a portfolio változatban "*"-gal jelölt) **a Bonferroni után nem szignifikáns**.

**Stratégiai következmény**: a "csak a PCR + OTM call inverz" megoldás **statisztikailag erősebb alapokon áll**, mint a "PCR + RVOL + OTM call inverz" megoldás. A Bonferroni-korrekció **konzervatív** (FDR-alapú Benjamini-Hochberg lazább lenne), de a portfolio változatban szereplő javaslatok **erre érzékenyek**.

## 4.4 A 60-trade dark pool audit — statisztikai erő

A 2026-05-08-i belső dark pool audit (per-ticker UW retrospective audit, $n = 60$ ügylet a W17-W19 időszakból):

| Mutató | Érték | p-érték | 95% CI |
|--------|-------|---------|--------|
| Pearson $\rho(\text{dp\_pct}, R)$ | -0,140 | 0,285 | [-0,374, +0,109] |
| Pearson $\rho(\text{dp\_pct}, r_{\text{per share}})$ | **-0,265** | **0,041** | [-0,481, -0,011] |
| Spearman $\rho_s(\text{dp\_pct}, r_{\text{per share}})$ | **-0,327** | **0,011** | [-0,533, -0,082] |

**A `r_{per share}`-en a kapcsolat statisztikailag szignifikáns** (Pearson p=0,041, Spearman p=0,011), **de** a 95% CI **széles**: [-0,481, -0,011] a Pearson r-re. Ez azt jelenti, hogy a true Pearson r értéke $-0{,}48$ és $-0{,}01$ között lehet — nagy bizonytalanság.

A statisztikai erő-elemzés: $n = 60$ esetén, $\alpha = 0{,}05$, 80% power-hez szükséges effektméret:

$$|\rho_{\min}| \approx (1{,}96 + 0{,}84)/\sqrt{57} \approx 0{,}371$$

**A megfigyelt $|\rho| = 0{,}265$ ALATT van a power-küszöb 0,371-nek**. Ez azt jelenti, hogy:
- **Type II error-rate** (nem detektált true effect): a 60 napi adat **alulvizsgált** a $|\rho| = 0{,}265$ effektre. Ha a true effect ekkora, **csak ~40-50% valószínűséggel** detektáljuk a 60-trade mintán.
- A megfigyelt szignifikancia $p = 0{,}041$ **éppen átlépi** a hagyományos 0,05 küszöböt; egy **többszörös teszt** (UW dark pool × 7 más al-komponens = 8 teszt) Bonferroni-korrigálva $\alpha = 0{,}00625$, amit **NEM lépi át** a $p = 0{,}041$.

**Stratégiai értelmezés**: a 60-trade audit **érdemleges hipotézis**, de **NEM végleges igazság**. A "UW marad" döntés Day 90-i újraértékelése, $n \approx 120 - 180$ ügyletes mintán, **megerősítheti vagy cáfolhatja** ezt a finding-ot. **3 hónap shadow log adata** lehetővé teszi a true effect szignifikáns becslését (ha $|\rho_{\text{true}}| > 0{,}21$, $n = 180$ esetén 95% szignifikancia detektálható).

## 4.5 A költségmodell és az effektív Sharpe-degradáció

A teljes éves súrlódás a 1.3 fejezet szerint:

$$C_{\text{annual}} = c_{\text{comm,annual}} + s_{\text{annual}} \cdot \text{Equity} + c_{\text{data,annual}}$$

A 60 napi minta extrapolálva:

| Komponens | Éves költség | Éves drag |
|-----------|--------------|-----------|
| Commission | $8 400 (= $35 × 240 nap) | 8,4% |
| Slippage | $3 000 - $5 000 (becsült) | 3-5% |
| Adat | $7 980 (= $665 × 12) | ~8,0% (a frissített API_STACK alapján) |
| **Total** | **~$19 000 - 21 000** | **~19-21%** |

**Megjegyzés**: a portfolio változatban szereplő $354/hó adat **hibás**; a frissített API_STACK.md szerint $665/hó.

A break-even bruttó alpha-cél tehát **éves ~19-21%**, ami a Sharpe-ratiónál:

$$\text{SR}_{\text{break-even}} \approx \frac{0{,}19 - r_f}{\sigma_R}$$

ha $r_f = 0{,}05$ (US 10y) és $\sigma_R \approx 0{,}15$ (a 60 napi minta standard hibája extrapolálva), akkor $\text{SR} \approx 0{,}93$. **Ez nagyon ambíciózus** — a hedge fund top decile $\text{SR} \in [0{,}8, 1{,}5]$ tartomány, **a profit a súrlódás után**. **A jelenlegi rendszer súrlódás-szintje tehát egy top decile hedge fund teljesítményt igényel** a break-even-hez.

## 4.6 Kelly criterion — a rendszer expectancy-je

A 378 ügyletes minta empirikus statisztikái:

- Win rate: $p = 0{,}466$
- Loss rate: $q = 1 - p = 0{,}534$
- Avg win: $W = +\$32{,}95$ (T1) / $+\$286$ (T2) / $+\$3{,}36$ (MOC) — kombinált $\bar{W} \approx +\$15{,}07$
- Avg loss: $L = -\$78{,}87$ (SL) / $-\$98{,}50$ (LossExit) / kombinált $\bar{L} \approx -\$92{,}56$

A Kelly fraction:

$$f^* = \frac{\bar{W}}{|\bar{L}|} \cdot p - q = \frac{15{,}07}{92{,}56} \cdot 0{,}466 - 0{,}534 = 0{,}076 - 0{,}534 = -0{,}458$$

**A Kelly fraction NEGATÍV**: $f^* = -0{,}458$. Ez **a matematikai kvalifikáció arra**, hogy a rendszer **negatív expectancy-jű**: minden ügylet várt hozama negatív, és az optimális position size **0** (vagy **short** lenne, ha shortolnánk a saját rendszer signalt-jét).

**Egy adat-intuíció ellenőrzéssel**: a teljes 378 ügyletes nettó hozam $-\$1 \, 460$, ami **konzisztens** a negatív expectancy-vel.

**Stratégiai következmény**: a jelenlegi rendszer **a 60 napi adat alapján negatív expectancy-jű**. Egy **0 expectancy** (break-even) eléréséhez vagy:
- (a) A win rate $p$ növelése — pl. a magas pontszám paradoxon orvoslása révén
- (b) Az átlag-veszteség $|\bar{L}|$ csökkentése — a loss-exit / SL mechanika javítása
- (c) Az átlag-nyereség $\bar{W}$ növelése — a T1/T2 cél revízió

Az `f^* = 0` küszöbhöz a Kelly egyenletből visszafejtve: $p \cdot \bar{W} = q \cdot |\bar{L}|$, ami a jelenlegi $|\bar{L}| = \$92{,}56$ esetén megköveteli $p \cdot \bar{W} = 0{,}534 \cdot 92{,}56 = 49{,}43$. **Ha $p$ konstans 0,466**, akkor $\bar{W}$ kell hogy legyen $49{,}43/0{,}466 = \$106{,}07$ — vagyis a jelenlegi $\$15{,}07$ átlag-nyereséget **7×-esére** kéne növelni. **Ez extrém**, és **a kis profit-küszöbök (T1 = 1,25 ATR, T2 = 2 ATR) strukturális gyengeségét** mutatja.

---

# 5. Strukturális diagnózis — bias-variance, multiple comparison, Kelly expectancy

## 5.1 A "magas pontszám paradoxon" mint regression-to-the-mean jelenség

A Q3 quintile $\bar{R} = -\$17{,}88$ és Q5 $\bar{R} = -\$8{,}91$ **strukturális regression-to-the-mean** mintát mutat. Egy lehetséges modellje:

$$R_i = \mathbb{E}[R | S_i] + \epsilon_i, \quad \epsilon_i \sim \mathcal{N}(0, \sigma^2)$$

Ha a "valódi" $\mathbb{E}[R | S]$ függvény **fordított-U** alakú (lokális maximum a Q2-ben), akkor a Q5-ben a **noise + kicsi true negative drift** kombinációja a megfigyelt mintát eredményezi. **Egy ilyen U-alakú** kapcsolat valószínűsíthető a:

- **Crowdedness**: a magas pontszám = több ticker a portfolio-ban = nagyobb verseny a flow-ért
- **Slippage-skálázás**: a magas pontszám gyakran alacsony likviditású ticker = nagyobb slippage
- **Mean-reversion**: a magas pontszám gyakran "már elhasznált" momentum = visszafordulás

A megoldás javaslata: **non-linear scoring függvény** (pl. a Q2 körüli optimum-zónába tolt logisztikus függvény), de **kis n** (378 ügylet) miatt a **non-linear modell könnyen overfittet** — a Bonferroni / cross-validation szigorúan szükséges.

## 5.2 Az időtáv-paradoxon mint Brown-folyamat skálázási probléma

A flow signal $\xi_t$ feltételezett **információs tartalma** $h$-step-ahead:

$$I(\xi_t; r_{t+h}) = H(r_{t+h}) - H(r_{t+h} | \xi_t)$$

ahol $H$ a Shannon-entrópia. Egy **martingale price process** esetén:

$$I(\xi_t; r_{t+h}) \approx \rho^2 \cdot h$$

amennyiben $\rho(\xi_t, r_{t+h})$ a $h$-step korreláció (egyszerűsítve). **Ez azt jelenti, hogy a mutual information lineárisan nő a holding period-pel**.

**Ha** a flow signal valódi mutual information-ja $h = 1$ napon $\sim 0{,}02$ (Pearson r ~+0,14), akkor egy $h = 5$ napi holding period **elvileg** $\sim 0{,}10$ mutual information-t adhat — **5× erősebb** signalt.

**Kvalifikáció**: ez egyszerűsített modell. A valós piacban a flow signal **mean-reverting** (a piaci hatékonyság miatt az információ elavul), és a **noise variancia is nő** $h$-val. **A kvantitatív backtest** (B opció Fázis 1) szükséges a valódi $I(\xi_t; r_{t+h})$ függvény empirikus becslésére $h \in \{1, 3, 5, 7\}$ napi időablakokra.

## 5.3 A loss-exit / bracket SL bug — formális leírás

A duplikált zárás bug egy **race condition**:

```
t = 0:    L_t = +Q (long pozíció)
t = τ_LE: L_t → 0 (loss-exit MARKET SELL Q)
t = τ_BR: L_t → -Q (bracket SL fire-ol, ELADJA még Q-t, short nyit)
```

Ahol $\tau_{LE} < \tau_{BR}$ (a loss-exit korábban triggerel, mert a -2% küszöb alacsonyabb, mint a -1,5 ATR ≈ -3%-os SL küszöb).

A **probabilitás-elemzés**: a -2% és -3% közötti ár-tartomány tipikusan $\sim 1\%$-pont széles. A 60 napi adatban **2 dokumentált eset** (DTE, SQM) → a bug **frequency rate**:

$$f_{\text{bug}} = 2/60 \approx 3{,}3\%$$

**Ez nem véletlen**: a bug pont akkor triggerelődik, amikor a piaci ár **gyorsan átmegy** a -2% és -3% közötti tartományon, ami **nagy volatilitás-eseményeknél** gyakori. A 60 napi minta tehát **alulbecsli** a bug igazi frekvenciáját — egy magasabb-volatilitás regime-ben (Goldilocks-ról Recession-re átmenet) **könnyen elérheti az 5-10%-os ügylet-arányt**.

**Megoldás**: a `cancel_bracket_orders()` előbb-hívás a `loss-exit` MARKET SELL előtt → $f_{\text{bug}} \to 0$.

## 5.4 A short ág inaktivitása — a long-only stratégia korlátai

A jelenlegi rendszer **mindig long**: $\mathcal{P}_t = \mathcal{P}_t^{\text{long}}$, $\mathcal{P}_t^{\text{short}} = \emptyset$. **Ez egy fontos korlát**, mert:

- **A flow signal szimmetrikus** lehet: a magas put-call ratio (PCR) **negatív bullish signal**, de **lehetne pozitív bearish signal** is — egy short pozíció megnyitására.
- **Bearish piaci regime-ben** (RED BMI vagy CRISIS Cross-Asset) a long-only rendszer **csak veszthet** (vagy cash-ben marad); a short ág **alpha-t generálhatna**.
- **Sharpe degradation**: a long-only stratégia $\beta_{\text{portfolio}} \approx 1$ (a piaccal együtt mozog), ami **csökkenti a Sharpe-t** szemben egy long/short market-neutral stratégiával ($\beta \approx 0$).

A 60 napi adatban a **BMI mindig YELLOW** és a **Stagflation regime tartós** — egy short ág **valószínűleg** nem segített volna jelentősen, **de** egy **regime-érzékeny short-aktiváció** (pl. CRISIS-ben automatikus short bekapcsolás) **a graceful exit alternatíva**, ha a long oldal nem ad alpha-t.

---

# 6. A 2026 áprilisi átalakítás mérlege (formális mátrixban)

## 6.1 A 13 javaslat státusz-mátrixa

Legyen $\mathbf{p} = (p_1, p_2, \ldots, p_{13})^T$ a 13 javaslat státusz-vektora, ahol $p_i \in \{1, 0{,}5, 0\}$:

| $i$ | Javaslat | $p_i$ | Várt Δ-alpha (havi) |
|-----|----------|-------|----------------------|
| 1 | freshness_bonus 1,5 → 1,0 | 1 | +0,1% |
| 2 | rs_spy_bonus 40 → 15 | 1 | +0,2% |
| 3 | weights flow-first | 1 | +0,3% |
| 4 | T1 0,75 → 1,5 ATR | 0,5 | +0,1-0,2% |
| 5 | T2 3,0 → 2,0 ATR | 1 | +0,1% |
| 6 | bracket 33/67 → 50/50 | 1 | +0,1% |
| 7 | dinamikus pozíciószám | 0 | +0,5-1,0% |
| 8 | submit 15:45 → 16:15 | 1 | +0,2% |
| 9 | mms kikapcsolás | 1 | +0,1% |
| 10 | call wall T1 kikapcsolás | 0 | +0,1-0,2% |
| 11 | VWAP guard egyszerűsítés | 0 | +0,1% |
| 12 | multiplier chain egyszerűsítés | 0,5 | +0,1% |
| 13 | flow al-komponens dekompozíció | 1 | (elemzés) |

**Implementációs pontszám**: $\sum p_i = 8{,}5/13 \approx 65\%$.

**Implementálatlan elemek várt hatása** ($p_i = 0$):
- Dinamikus pozíciószám (i=7): +0,5-1,0% havi alpha
- Call wall T1 kikapcsolás (i=10): +0,1-0,2%
- VWAP guard egyszerűsítés (i=11): +0,1%

**Total nem-implementált alpha-potenciál**: ~+0,7-1,3% havi.

## 6.2 A 13. pont (flow al-komponens dekompozíció) — hipotézis-cáfolat

A 2026 áprilisi terv **a priori hipotézist** fogalmazott meg: a "modern institutional flow" indikátorok (dark pool %, block trade, buy pressure) **dominánsan prediktívek**.

A 13. javaslat futtatott elemzése **megcáfolja** ezt:

$$H_0^{\text{prior}}: \rho_{\text{dp}} > \rho_{\text{PCR}} \quad \text{és} \quad \rho_{\text{block}} > 0$$

**Empirikus eredmény**: $\rho_{\text{dp}} = 0$ (inaktív adat), $\rho_{\text{PCR}} = +0{,}203$, $\rho_{\text{block}} = -0{,}117$. **A prior hipotézis cáfolva** mind a két reláción.

**Bayesi értelmezés**: a prior hipotézis **erős** volt (a "modern institutional flow" branding széleskörű a iparágban), **de** a 232-ügyletes posterior **inkább a "klasszikus opciós flow" felé csúsztatja a hihető súlyt**. A Bayes-faktor:

$$BF = \frac{P(\text{adat} | H_{\text{classical}})}{P(\text{adat} | H_{\text{modern}})} \approx 5 - 10$$

(durva becslés a posterior likelihood ratiókból). Ez **strong evidence for H_classical**.

**Stratégiai következmény**: az API_STACK újratervezésénél (Polygon → Polygon + UW vs Polygon-only) a **Bayes-priorral** kalibrált döntés:
- **UW marad** (Tamás 2026-05-08-i döntés alapján): $P(\text{ad alpha-t}) \in [0{,}3, 0{,}6]$ — **közepes** valószínűség, hogy érdemleges edge-et ad
- **Kannibalizálás** (Polygon-only): $P(\text{kvalitás-veszteség}) \in [0{,}1, 0{,}4]$ — **alacsony-közepes** veszteség

A **decision-theoretic választás** Day 90-i újraértékelésig **az UW megtartása** reasonable; a 3 hónap shadow log alatt $n \approx 180$ ügylet várható, ami a $|\rho_{\text{dp}}| = 0{,}265$ effekt detektálásához **elég power**.

---

# 7. Három stratégiai irány — döntéselméleti keret

## 7.1 A három opció formalizálása

Legyen $A$ az opció A (inkremeális finomítás), $B$ a B (multi-day swing), $C$ a C (hibrid kísérletek). Mindegyik opcióhoz tartozik egy:
- $\Delta\mu_X$: várt havi alpha-növekedés (random változó, prior-alapú)
- $\sigma_X$: a $\Delta\mu$ standard hibája
- $\tau_X$: implementációs idő (hetekben)
- $\Pi_X$: prior valószínűség, hogy az opció **pozitív** alpha-t ad

A három opció paraméterei:

| Opció | $\mathbb{E}[\Delta\mu]$ | $\sigma$ | $\tau$ | $\Pi(\Delta\mu > 0)$ |
|-------|--------------------------|----------|--------|----------------------|
| A | +0,75% | 0,3% | 8 hét | 0,75 |
| B | +1,25% | 0,8% | 16 hét | 0,55 |
| C | +0,85% | 0,3% | 3 hét | 0,70 |

**Megjegyzések**: a B opció **magasabb várt értékkel** és **magasabb varianciával**, **alacsonyabb prior valószínűséggel** rendelkezik. A C opció **a leggyorsabb és legbiztosabb**, **de** a **legkisebb maximum-potenciállal**.

## 7.2 Az opcionalitás értéke (real options framework)

A B opció két fázisú: **Fázis 1 backtest** (low cost, ~$h_{B1} = 6$ hét) → **Fázis 2 implementáció** ($h_{B2} = 10$ hét). A backtest egy **opció**: ha a backtest negatív, **abandon** a B-t, csak a Fázis 1 költségét (idő + erőforrás) viseljük; ha pozitív, folytatjuk a Fázis 2-vel.

A real option értéke:

$$V_B = \mathbb{E}[\max(\text{Fázis 2 alpha}, 0)] - h_{B1} \cdot c_{\text{opportunity}}$$

ahol $c_{\text{opportunity}}$ az opportunity cost a Fázis 1-en során (más fejlesztés időigénye).

**Ha** a Fázis 1 backtest sikertelen ($\Pi(\text{Fázis 1 pozitív}) = 0{,}55$), a Fázis 2 elmarad → a teljes $V_B$ kisebb, mint a deterministic kalkuláció.

**Decision-theoretic értelmezés**: a B opció Fázis 1 (backtest) **alacsony költségű opció** a B teljes implementáció lehetőségére. **Ez a magyarázata** annak, hogy a 7.5 fejezetben (a portfolio változatban) az ajánlat **A + C kombináció + B párhuzamos R&D** — a B Fázis 1 a **real option exercise**, ami Day 90-ig **nem köt eleget**.

## 7.3 Bayesi update a Day 90 értékelésnél

Day 90-en a 30 napi új adat ($n_{\text{new}} \approx 60-90$ ügylet) Bayes-update-elhetjük a posteriort:

$$P(\Delta\mu_X | \text{prior, new data}) \propto P(\text{new data} | \Delta\mu_X) \cdot P(\Delta\mu_X)$$

A Day 90-i döntéshozási keret:

| Eredmény | A + C alpha | B Fázis 1 backtest | Döntés |
|----------|--------------|---------------------|--------|
| 1 | $> +0{,}5\%$ | bármi | **Élő pénzes ($10k)** |
| 2 | $\in [-0{,}5\%, +0{,}5\%]$ | pozitív | **B Fázis 2 indítás, paper folytatás** |
| 3 | $< -0{,}5\%$ | pozitív | **B Fázis 2 indítás (+ leállás A)** |
| 4 | $< -0{,}5\%$ | negatív | **Graceful exit** |

A döntési mátrix **explicitté teszi** a feltételes válaszokat — egyik kimenet sem **fixed**, mind az új adat-feltételen múlik.

---

# 8. Kockázatkezelés és sztochasztikus modellek

## 8.1 Drawdown-elemzés és Maximum Drawdown

A 60 napi minta empirikus drawdown-jai:
- Maximum drawdown: $-2{,}13\%$ (kb. W18 vége / W19 D2 körül)
- A drawdown-statisztika: az "élesítési" feltétel szerint a 3% drawdown **circuit breaker** triggert.

A kumulatív hozam $C_t = \sum_{s=1}^{t} R_s$ trajektóriájára a **expected maximum drawdown** Brown-folyamat alatt:

$$\mathbb{E}[\text{MDD}_T] \approx 0{,}51 \cdot \sigma \sqrt{T}$$

ahol $T$ az időhorizont. A 60 napi adatra $\sigma_{\text{daily}} \approx 0{,}007$ ⇒ $\mathbb{E}[\text{MDD}_{60}] \approx 0{,}51 \cdot 0{,}007 \cdot \sqrt{60} \approx 0{,}027$ = 2,7%. **A megfigyelt MDD = 2,13% konzisztens** a Brown-folyamat predikcióval.

A **3% circuit breaker** valószínűsége egy 60 napi időszakban:

$$P(\max_t |C_t - \max_{s<t} C_s| > 0{,}03) \approx 0{,}45$$

(durva becslés). **Ez magas valószínűség**, ami azt jelzi, hogy a circuit breaker egy 60-90 napi futáson **valószínűleg többször is fire-ol** — a stratégia **strukturálisan kockázatos** ezen a teljesítmény-szinten.

## 8.2 Value-at-Risk (VaR)

A 95%-os egyzapsi VaR:

$$\text{VaR}_{0{,}95} = -\text{percentile}_{0{,}05}(R_i)$$

A 60 napi minta empirikus 5. percentilise: $\approx -\$120$ /ügylet, ami $\sim 2{,}5\%$ pozíciónként. Ha 5 pozíciót tartunk → portfolio VaR $\approx 12{,}5\%$ (a worst-case minden pozíción veszít). **A jelenlegi keret max 3% account-szintű** VaR-t enged → ez a **strukturális ellentmondás** a single-position vs portfolio VaR között.

**A korreláció-szabályok** (max 2/szektor, max 3/csoport) **csökkentik** a portfolio VaR-t kb. 8-9%-ra, **de még mindig magasabb**, mint a 3% circuit breaker.

## 8.3 Tail-risk és heavy-tailed eloszlás

A 60 napi P&L empirikus statisztikái:
- Skewness: $-1{,}45$ (heavy left tail)
- Excess kurtosis: $4{,}87$ (heavy tails — leptokurtic)

**A normál eloszlás feltevése** alulbecsli a tail-kockázatot. Egy **Student-t eloszlás** ($\nu = 4-5$ szabadsági fok) jobban illik az adatokra. A Student-t alapú VaR:

$$\text{VaR}_{0{,}95}^{\text{t-dist}} \approx 1{,}5 \times \text{VaR}_{0{,}95}^{\text{normal}}$$

azaz **1,5×-es korrekció** a normál-alapú VaR-hoz képest.

## 8.4 Sztochasztikus integráció a multi-day backtest-hez

A B opció Fázis 1 backtest formalizálása:

$$\mathbb{E}[R^{(h)}_i | \xi_i] = \int_0^h \mu(\xi_i, s) \, ds + \text{noise}$$

ahol $\mu(\xi_i, s)$ a flow signal $\xi_i$ feltételes drift-je $s$-step-ahead, és $h$ a holding period (1, 3, 5, 7 nap). A backtest **kvantitatív kérdése**:

$$h^* = \arg\max_h \mathbb{E}[R^{(h)}_i | \xi_i] - \text{cost}(h) - \text{risk}(h)$$

ahol $\text{cost}(h)$ a turnover-csökkenés (kevesebb commission), és $\text{risk}(h)$ az overnight gap-kockázat (növekvő $h$-val).

A backtest **NEM ad** garanciát; **lehet**, hogy $h^* = 0$ (intraday optimális) — ami a B opció elhagyását indokolja.

## 8.5 Position-sizing optimization a Kelly criterion alapján

A Kelly fraction számítása (4.6 fejezet): $f^* = -0{,}458$. Mivel $f^* < 0$, a **matematikai konkluzió**: **a jelenlegi rendszer alkalmazva sem 0,7%, sem ennél kisebb pozíciókkal nem ad pozitív expected value-t**.

A **fractional Kelly** (a piaci gyakorlatban gyakori, $f = 0{,}25 \cdot f^*$) értelmetlen, mert a Kelly maga negatív. **Ez a leglényegesebb matematikai bizonyítéka annak, hogy a rendszer fundamentális átalakítása szükséges** — pusztán a position size csökkentésével **nem javítható**.

---

# 9. Függelékek

## 9.1 A scoring funkcionál teljes alakja

$$S_j(t) = 0{,}60 \cdot \phi_j^{\text{flow}}(t) + 0{,}30 \cdot \phi_j^{\text{tech}}(t) + 0{,}10 \cdot \phi_j^{\text{funda}}(t) + \Delta S_j^{\text{sect}}$$

ahol:

$$\phi_j^{\text{flow}}(t) = 50 + b_1 g_1(\text{RVOL}) + b_2 g_2(\text{DP\%}) + b_3 g_3(\text{PCR}) + \ldots + b_7 g_7(\text{Squat})$$

$$\phi_j^{\text{tech}}(t) = b_{\text{RSI}} g_{\text{RSI}}(\text{RSI}_{14}) + b_{\text{SMA}} \mathbb{1}[\text{Price} > \text{SMA}_{50}] + b_{\text{RS}} \mathbb{1}[\text{RS\_3M} > \text{SPY}_{3M}]$$

$$\phi_j^{\text{funda}}(t) = 50 + \sum_k b_k^{\text{funda}} \cdot \mathbb{1}[\text{cond}_k]$$

**EWMA simítás**: $\tilde{S}_j(t) = 0{,}182 \cdot S_j(t) + 0{,}818 \cdot \tilde{S}_j(t-1)$.

## 9.2 A multiplier chain teljes alakja

$$M_{\text{total}}(j) = \text{clamp}\left( M_{\text{VIX}}(t) \cdot M_{\text{GEX}}(j, t) \cdot M_{\text{target}}(j) \cdot M_{\text{contradiction}}(j), \; 0{,}25, \; 2{,}0 \right)$$

ahol:

$$M_{\text{VIX}}(t) = \max(1{,}0 - 0{,}02 \cdot \max(\text{VIX}_t - 20, 0), \; 0{,}1)$$

$$M_{\text{GEX}}(j, t) = \begin{cases} 1{,}0 & \text{GEX}_j > \theta_+, \text{ low-vol} \\ 0{,}5 & \text{GEX}_j < \theta_-, \text{ low-vol} \\ 0{,}6 & \text{high-vol regime} \\ 0{,}75 & \text{undetermined} \end{cases}$$

$$M_{\text{target}}(j) = \begin{cases} 0{,}60 & P_j > 1{,}50 \cdot T_j^{12m} \\ 0{,}85 & P_j > 1{,}20 \cdot T_j^{12m} \\ 1{,}0 & \text{egyébként} \end{cases}$$

$$M_{\text{contradiction}}(j) = \begin{cases} 0{,}80 & \bigvee_{c} \text{cond}_c(j) \\ 1{,}0 & \neg \bigvee_{c} \text{cond}_c(j) \end{cases}$$

## 9.3 Statisztikai erő-tábla

A Pearson korrelációs együttható szignifikancia-elemzéséhez ($\alpha = 0{,}05$ kétoldali, 80% power):

| $n$ | $|\rho_{\min}|$ |
|-----|------------------|
| 30 | 0,495 |
| 60 | 0,353 |
| 120 | 0,251 |
| 200 | 0,196 |
| 378 | 0,144 |
| 500 | 0,125 |
| 1000 | 0,089 |

**Értelmezés**: a 378-trade scoring validation **képes** detektálni $|\rho_{\text{true}}| \geq 0{,}144$ effektet 80%-os valószínűséggel. A 60-trade dark pool audit **CSAK** $|\rho_{\text{true}}| \geq 0{,}353$ effekt detektálására képes — a megfigyelt $0{,}265$ **alulvizsgált**.

## 9.4 Bonferroni-korrekció a multi-comparison esetekre

| Tesztek száma | $\alpha_{\text{Bonferroni}}$ | $|\rho_{\text{crit}}|$ ($n=232$) |
|----------------|-------------------------------|----------------------------------|
| 1 | 0,05 | 0,128 |
| 7 (al-komponensek) | 0,00714 | 0,176 |
| 14 (al-komp × 2 stat) | 0,00357 | 0,193 |
| 50 (extrém) | 0,001 | 0,210 |

## 9.5 A Kelly criterion részletes számítás

A 378 ügyletes minta:
- $p$ (win rate) = 0,466
- $q$ (loss rate) = 0,534
- Avg win $\bar{W}$:
  - T1 (n=36): $+\$32{,}95$
  - T2 (n=3): $+\$286{,}03$
  - Trail (n=3): $+\$33{,}39$
  - MOC profit (n=140): $+\$3{,}36$ (becsült profit-half)
  - **Súlyozott átlag**: $\bar{W} = (36 \times 32{,}95 + 3 \times 286{,}03 + 3 \times 33{,}39 + 140 \times 3{,}36)/(176) \approx +\$15{,}07$
- Avg loss $\bar{L}$:
  - SL (n=15): $-\$78{,}87$
  - LossExit (n=32): $-\$98{,}50$
  - MOC loss (n=140): $-\$3{,}36$ (becsült loss-half)
  - **Súlyozott átlag**: $\bar{L} = (15 \times 78{,}87 + 32 \times 98{,}50 + 140 \times 3{,}36)/(187) \approx -\$24{,}67$ (a MOC mely félre megy → nagyobb mintán változik)

**Konzervatív Kelly** (csak a determinisztikus exit-ek):
- $\bar{W}_{\text{det}} = (36 \times 32{,}95 + 3 \times 286{,}03 + 3 \times 33{,}39)/42 \approx +\$50$
- $\bar{L}_{\text{det}} = (15 \times 78{,}87 + 32 \times 98{,}50)/47 \approx -\$92{,}56$
- $f^* = 0{,}50 \cdot 50/92{,}56 - 0{,}50 = 0{,}27 - 0{,}50 = -0{,}23$ (még mindig negatív)

A negatív Kelly **strukturálisan robusztus** különböző számítási módokon.

## 9.6 A 60-trade UW dark pool audit egyenlőtlensége

A `r_per share` és `dp_pct` közötti Pearson r 95% konfidencia-intervallum (Fisher z-transzformáció):

$$z = \tanh^{-1}(r) = \tanh^{-1}(-0{,}265) = -0{,}272$$

$$\text{SE}(z) = 1/\sqrt{n-3} = 1/\sqrt{57} = 0{,}132$$

$$z_{0{,}025} = -0{,}272 - 1{,}96 \cdot 0{,}132 = -0{,}532$$
$$z_{0{,}975} = -0{,}272 + 1{,}96 \cdot 0{,}132 = -0{,}012$$

Visszatranszformálva:
$$r_{0{,}025} = \tanh(-0{,}532) = -0{,}486$$
$$r_{0{,}975} = \tanh(-0{,}012) = -0{,}012$$

**95% CI**: $\rho \in [-0{,}486, -0{,}012]$. A felső határ kvázi 0, ami azt jelenti, hogy **a true Pearson r MAJDNEM ZÉRO is lehet** — a 60-trade audit **nagyfokú bizonytalansággal** jelzi a valódi effektméretet.

## 9.7 A Sharpe ratio kvalifikálása

A 60 napi minta empirikus Sharpe ratio (annualized):

$$\text{SR}_{60} = \frac{\bar{R}/\$E - r_f}{\sigma_R/\$E} \cdot \sqrt{N_{\text{annual}}/T}$$

ahol $\bar{R} \approx -\$3{,}15$/ügylet, $\sigma_R \approx \$50$/ügylet (becsült), $\$E = \$100\,000$, $r_f = 0{,}05$, $N_{\text{annual}} \approx 1500$, $T = 60$.

$$\text{SR}_{60} \approx \frac{-3{,}15/100000 \cdot 1500 - 0{,}05}{50/100000 \cdot \sqrt{1500/60}} = \frac{-0{,}047 - 0{,}05}{0{,}0025} \approx -38{,}8$$

**Ez extrém negatív SR** — a 60 napi adat **statisztikailag nem-elhanyagolható alulteljesítést** mutat a kockázat-arányosított kontextusban.

## 9.8 Összefoglaló — a leglényegesebb matematikai finding-ok

1. **Pearson r ≈ 0** (kompozit score vs P&L) — 95% CI a true effekten: $[-0{,}10, +0{,}10]$. **Strong evidence** a "small effect" tartományra.
2. **Kelly criterion negatív**: $f^* = -0{,}23$ (konzervatív) — **a rendszer matematikailag negatív expectancy-jű**.
3. **Sharpe ratio kvalifikálva**: $\text{SR}_{60} \approx -38{,}8$ (extrém negatív), de a futási minta korlátozott.
4. **Bonferroni-korrigált flow al-komponens szignifikancia**: csak **PCR és OTM call** marad szignifikáns 14 teszt után. Az **RVOL (+0,147)** Bonferroni után **nem szignifikáns**.
5. **60-trade dark pool audit**: $|\rho| = 0{,}265$ marginálisan szignifikáns, de **alulvizsgált** a $|\rho| < 0{,}353$ effekt-küszöbnél. A 95% CI széles ($-0{,}486$ - $-0{,}012$). **Day 90 újraértékelés** ($n \approx 180$) ad megfelelő power-t.
6. **Loss-exit / bracket SL bug** frequency rate: $\approx 3{,}3\%$ a 60 napi adatban; magasabb volatilitás regime-ben **5-10%** valószínűsíthető. **A javítás $f_{\text{bug}} \to 0$-ra hozza**.
7. **A makró-rezsim degenerált** a 60 napi adatban: $\text{Regime}_t = \text{YELLOW}$ minden $t$-re, a BMI **nem differenciál**.
8. **A multiplier chain információs degenerációja**: $M_{\text{VIX}} = 1{,}0$ minden $t$-re; $M_{\text{GEX}} = 0{,}75$ a esetek ~75%-ban. **Az effektív differenciálás csak $M_{\text{target}}$-en és $M_{\text{contradiction}}$-on múlik**.
9. **Az időtáv-paradoxon mutual information modell**: ha a flow signal valódi $h$-step korrelációja $\rho \approx 0{,}14$ ($h=1$), akkor $h=5$ esetén $I \cdot 5 \approx 5\rho^2 \approx 0{,}10$ — **5× erősebb signal egy multi-day holding alatt** (egyszerűsítés alapján).
10. **A break-even bruttó alpha-cél**: ~19-21% éves (a $665/hó adat-költség + commission + slippage), ami ~SR $= 0{,}93$ — **top decile hedge fund teljesítmény-szint**.

---

**A dokumentum vége.**

Ez az anyag a `2026-05-08-strategic-review-full.md` matematikai megfelelője. A fő finding-ok formálisan azonosak; a megfogalmazás formális (statisztikai erő, Bayesi update, Kelly criterion, sztochasztikus modellek), és bizonyos kvalifikálatlan állítások explicit kvantifikációt kapnak. A két dokumentum **párhuzamosan használható**: a kvalitatív és a kvantitatív megfogalmazás **egymás validálását** szolgálja.
