# Heizung-App für Android — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine installierbare Android-App, die die vier Heizungsdiagramme als Reiter zeigt, mit Pufferspeicher als Startbildschirm.

**Architecture:** Eigenständiges Gradle-Projekt unter `android/`, Kotlin + Jetpack Compose, ein einziger Activity. Daten kommen über HTTP von der bestehenden FastAPI (`/api/chart`); das Diagramm wird auf einem Canvas selbst gezeichnet. Die Python-Seite bleibt unverändert.

**Tech Stack:** Kotlin 2.0.21, AGP 8.7.3, Gradle 8.11.1, Jetpack Compose (BOM 2024.12.01), Material 3, OkHttp 4.12.0, kotlinx.serialization 1.7.3, DataStore Preferences 1.1.1, JUnit 4 + kotlinx-coroutines-test + MockWebServer.

**Spec:** `docs/superpowers/specs/2026-11-11-android-app-design.md`

## Global Constraints

- `minSdk 26`, `targetSdk 35`, `compileSdk 35`.
- Oberfläche ausschließlich deutsch; Zeitangaben in `ZoneId.of("Europe/Berlin")`.
- Nur lesend: keine Schreibaufrufe an die API.
- Keine Änderung an `src/heizung/**` oder an anderen Python-Dateien.
- Alle Dateien des neuen Projekts liegen unter `android/`.
- Diagramm ohne Fremdbibliothek: kein Plotly, keine WebView, keine Chart-Library.
- Spaltenreihenfolge der API ist fix: 17 analoge, dann 11 digitale Werte (Spec-Anhang).
- Kein Widget, keine Benachrichtigung, kein Offline-Cache, kein Fadenkreuz.
- Signatur: Release-Keystore aus GitHub-Secrets; fehlt er, wird debug-signiert und der Build bleibt lauffähig.

## Review Focus

Diese Fälle muss je eine Task mit einem Test abdecken — sie stehen in der Spec nicht, würden den Nutzer aber treffen:

1. `null`-Werte und Zeilen, in denen nur der Zeitstempel steht → Lücke in der Kurve, kein Absturz (Task 2, Task 3).
2. Server-Adresse mit Pfad oder ohne abschließenden Schrägstrich (`https://host/`, `https://host/heizung`) → korrekt zusammengesetzte URL, kein `//` und kein fehlender `/` (Task 2).
3. Leere Antwort `[]` und Antwort ohne jegliche Werte → Leerzustand statt Ausnahme (Task 2, Task 6).
4. Sommer-/Winterzeit: ein Tag hat 23 oder 25 Stunden; Achsenbeschriftung und Tagesfenster bleiben korrekt (Task 3).
5. Konstante Linie und Ausreißer (Solarstrahlung 1000 neben 0) → Mindestspanne, keine Division durch null, kein Absturz (Task 6).

---

### Task 1: Werkzeuge und ein leeres Projekt, das baut

**Files:**
- Create: `android/settings.gradle.kts`, `android/build.gradle.kts`, `android/app/build.gradle.kts`, `android/gradle.properties`, `android/local.properties` (nicht eingecheckt), `android/app/src/main/AndroidManifest.xml`, `android/app/src/main/java/de/zwotzie/heizung/MainActivity.kt`, `android/app/src/main/res/values/strings.xml`, `android/.gitignore`
- Create: `android/app/src/test/java/de/zwotzie/heizung/SmokeTest.kt`

**Interfaces:**
- Consumes: nichts.
- Produces: baubares Gradle-Projekt mit `de.zwotzie.heizung` als Anwendungspaket; `./gradlew :app:testDebugUnitTest` läuft.

- [ ] **Step 1: Werkzeuge prüfen**

Bereits vorhanden (nicht neu installieren):

- JDK 17: `/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home`
- Android-SDK: `ANDROID_HOME=/opt/homebrew/share/android-commandlinetools` mit `platforms/android-35`, `build-tools/35.0.0`, `platform-tools`

```bash
export JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
"$JAVA_HOME/bin/java" -version        # erwartet 17.x
ls "$ANDROID_HOME/platforms/android-35" "$ANDROID_HOME/build-tools/35.0.0"
```

Erwartet: Java 17, beide SDK-Verzeichnisse vorhanden.

Hinweis: Das lokal installierte Java 27 und die JBR 25 von IntelliJ sind für Gradle 8.11.1 zu neu — für alle Gradle-Aufrufe `JAVA_HOME` auf das JDK 17 setzen.

- [ ] **Step 2: Gradle-Wrapper erzeugen**

```bash
cd /tmp && curl -L https://services.gradle.org/distributions/gradle-8.11.1-bin.zip -o g.zip && unzip -q g.zip
mkdir -p <repo>/android && cd <repo>/android
/tmp/gradle-8.11.1/bin/gradle wrapper --gradle-version 8.11.1 --distribution-type bin
```

- [ ] **Step 3: Projektdateien anlegen**

`android/settings.gradle.kts`: Plugin-Management mit Repositories `google()` und `mavenCentral()`, `include(":app")`, `rootProject.name = "heizung"`.

`android/build.gradle.kts`: Plugins `com.android.application` 8.7.3, `org.jetbrains.kotlin.android` 2.0.21, `org.jetbrains.kotlin.plugin.compose` 2.0.21 — alle `apply false`.

`android/gradle.properties`: `org.gradle.jvmargs=-Xmx2048m`, `android.useAndroidX=true`, `kotlin.code.style=official`.

`android/app/build.gradle.kts`: `namespace = "de.zwotzie.heizung"`, `applicationId` gleich, `minSdk 26`, `targetSdk 35`, `compileSdk 35`, `buildFeatures { compose = true }`, `compileOptions`/`kotlinOptions` auf Java 17, Abhängigkeiten genau wie im Tech-Stack genannt, `versionCode = (findProperty("appVersionCode") as String?)?.toInt() ?: 1`, `versionName` analog.

`android/local.properties` mit `sdk.dir=/opt/homebrew/share/android-commandlinetools`.

`android/.gitignore` mit `local.properties`, `.gradle/`, `build/`, `*.iml`.

`MainActivity.kt`: setzt `setContent { Text("Heizung") }` in einem `MaterialTheme`.

`AndroidManifest.xml`: eine Activity, `android:exported="true"`, Label aus `strings.xml` (`Heizung`), kein `INTERNET`-Permission fehlt — `android.permission.INTERNET` aufnehmen.

- [ ] **Step 4: Test schreiben, der die Toolchain prüft**

```kotlin
class SmokeTest {
    @Test
    fun `zwei plus zwei ist vier`() {
        assertEquals(4, 2 + 2)
    }
}
```

- [ ] **Step 5: Bauen und testen**

Run: `cd android && JAVA_HOME=<jdk17> ./gradlew :app:testDebugUnitTest :app:assembleDebug`
Expected: `BUILD SUCCESSFUL`, `app/build/outputs/apk/debug/app-debug.apk` existiert.

- [ ] **Step 6: Commit**

```bash
git add android && git commit -m "feat(android): Gradle-Projekt für die Heizung-App"
```

---

### Task 2: Metrik-Katalog in API-Reihenfolge

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/data/MetricId.kt`, `.../data/Catalog.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/data/MetricIdTest.kt`, `.../data/CatalogTest.kt`

**Interfaces:**
- Consumes: nichts.
- Produces:
  - `enum class MetricId(val apiName: String)` mit 28 Einträgen in API-Reihenfolge (17 analog, dann 11 digital).
  - `enum class Unit(val label: String) { CELSIUS("°C"), PERCENT("%"), WATT_PER_M2("W/m²") }`
  - `data class SeriesSpec(val metric: MetricId, val label: String, val unit: Unit)`
  - `data class TabSpec(val title: String, val temperatures: List<MetricId>, val rows: List<MetricId>, val digital: List<MetricId>)`
  - `object Catalog { val tabs: List<TabSpec>; fun spec(metric: MetricId): SeriesSpec }`

- [ ] **Step 1: Test für die Spaltenreihenfolge schreiben**

```kotlin
class MetricIdTest {
    @Test
    fun `reihenfolge entspricht der api`() {
        assertEquals(28, MetricId.entries.size)
        assertEquals("kessel_rl", MetricId.entries[0].apiName)
        assertEquals("solar_ladepumpe_drehzahl", MetricId.entries[16].apiName)
        assertEquals("d_heizung_pumpe", MetricId.entries[17].apiName)
        assertEquals("heizung_an", MetricId.entries[27].apiName)
    }

    @Test
    fun `keine doppelten api-namen`() {
        assertEquals(28, MetricId.entries.map { it.apiName }.toSet().size)
    }
}
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `./gradlew :app:testDebugUnitTest --tests '*MetricIdTest*'`
Expected: FAIL, `MetricId` nicht auflösbar.

- [ ] **Step 3: `MetricId` anlegen** — 28 Enum-Einträge, Namen in Großbuchstaben, `apiName` exakt wie im Spec-Anhang.

- [ ] **Step 4: Katalog-Test schreiben**

```kotlin
class CatalogTest {
    @Test
    fun `vier reiter in fester reihenfolge`() {
        assertEquals(listOf("Puffer", "Solar", "Heizung", "Erzeuger"), Catalog.tabs.map { it.title })
    }

    @Test
    fun `puffer beginnt mit puffer-reiter und zeigt sieben temperaturen`() {
        val puffer = Catalog.tabs.first()
        assertEquals(7, puffer.temperatures.size)
        assertTrue(puffer.digital.isEmpty())
        assertEquals(MetricId.SPEICHER_1_KOPF, puffer.temperatures[2])
    }

    @Test
    fun `jede metrik hat einen anzeigenamen und eine einheit`() {
        MetricId.entries.forEach { assertTrue(Catalog.spec(it).label.isNotBlank()) }
        assertEquals(Unit.WATT_PER_M2, Catalog.spec(MetricId.SOLAR_STRAHLUNG).unit)
        assertEquals(Unit.PERCENT, Catalog.spec(MetricId.SOLAR_LADEPUMPE_DREHZAHL).unit)
    }
}
```

- [ ] **Step 5: Katalog anlegen** — Reihen gemäß Spec-Tabelle: Temperaturen in `temperatures`, Drehzahlen und Strahlung in `rows`, digitale Signale in `digital`. Anzeigenamen aus der Spec-Liste, Einheiten: alles `CELSIUS` außer `solar_strahlung` (W/m²) und den vier Drehzahl-Metriken (%). Farben kommen erst in Task 8, hier nicht.

- [ ] **Step 6: Tests laufen lassen**

Run: `./gradlew :app:testDebugUnitTest --tests '*MetricIdTest*' --tests '*CatalogTest*'`
Expected: PASS.

- [ ] **Step 7: Commit** — `git commit -m "feat(android): Metrik-Katalog mit API-Reihenfolge"`

---

### Task 3: JSON-Antwort der API lesen

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/data/ChartRow.kt`, `.../data/ChartJson.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/data/ChartJsonTest.kt`, `android/app/src/test/resources/chart_day.json`

**Interfaces:**
- Consumes: `MetricId`, `Catalog`.
- Produces: `data class ChartRow(val timestampSec: Long, val values: Map<MetricId, Double?>)`; `object ChartJson { fun parse(body: String): List<ChartRow> }` — wirft `IllegalArgumentException` bei kaputtem JSON, liefert `emptyList()` bei `[]`.

- [ ] **Step 1: Fixture schreiben**

`chart_day.json`: zwei Zeilen, erste Zeile mit allen 28 Werten (aufsteigend 1.0 … 28.0), zweite Zeile mit `null` in Spalte 2 und 3 sowie einem Zeitstempel 60 Sekunden später.

- [ ] **Step 2: Tests schreiben**

```kotlin
class ChartJsonTest {
    private fun fixture() = javaClass.getResource("/chart_day.json")!!.readText()

    @Test
    fun `spalten landen bei den richtigen metriken`() {
        val rows = ChartJson.parse(fixture())
        assertEquals(2, rows.size)
        assertEquals(1.0, rows[0].values[MetricId.KESSEL_RL])
        assertEquals(28.0, rows[0].values[MetricId.HEIZUNG_AN])
        assertEquals(1731250800L, rows[0].timestampSec)
    }

    @Test
    fun `null bleibt null und wird nicht zu null-komma-null`() {
        val rows = ChartJson.parse(fixture())
        assertNull(rows[1].values[MetricId.KESSEL_LADEPUMPE_DREHZAHL])
        assertNull(rows[1].values[MetricId.KESSEL_BETRIEBSTEMPERATUR])
    }

    @Test
    fun `leere antwort ergibt leere liste`() {
        assertEquals(emptyList<ChartRow>(), ChartJson.parse("[]"))
    }

    @Test
    fun `zeile mit nur zeitstempel wird nicht verworfen`() {
        val rows = ChartJson.parse("""[[1731250800]]""")
        assertEquals(1, rows.size)
        assertNull(rows[0].values[MetricId.KESSEL_RL])
    }

    @Test(expected = IllegalArgumentException::class)
    fun `kaputtes json wirft`() {
        ChartJson.parse("nicht json")
    }
}
```

- [ ] **Step 3: Tests laufen lassen, Fehlschlag bestätigen** — Run: `./gradlew :app:testDebugUnitTest --tests '*ChartJsonTest*'`, Expected: FAIL.

- [ ] **Step 4: `ChartJson` implementieren** — `Json.parseToJsonElement`, `JsonArray` durchlaufen; Element 0 als `Long` (Zahl oder Zahl-String), danach `MetricId.entries[i]` mit `row.getOrNull(i + 1)`, `JsonNull`/fehlend → `null`; nicht-numerische Werte → `null`. Wirft `IllegalArgumentException`, wenn das Wurzelelement kein Array ist.

- [ ] **Step 5: Tests laufen lassen** — Expected: PASS.

- [ ] **Step 6: Commit** — `git commit -m "feat(android): Chart-Antwort parsen"`

---

### Task 4: HTTP-Aufruf mit sauberer URL

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/data/ChartApi.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/data/ChartApiTest.kt`

**Interfaces:**
- Consumes: `ChartJson`, `ChartRow`.
- Produces:
  - `enum class Period { DAY, WEEK }`
  - `interface ChartApi { suspend fun fetch(date: LocalDate, period: Period): List<ChartRow> }`
  - `class HttpChartApi(baseUrl: () -> String, client: OkHttpClient = OkHttpClient()) : ChartApi`
  - `object ApiUrl { fun chart(baseUrl: String, date: LocalDate, period: Period): String }`
  - `class ChartApiException(message: String, val status: Int? = null) : Exception(message)`

- [ ] **Step 1: Tests für die URL-Zusammensetzung schreiben**

```kotlin
class ApiUrlTest {
    private val d = LocalDate.of(2026, 11, 11)

    @Test
    fun `ohne schraegstrich am ende`() {
        assertEquals("https://h.example/api/chart?date=2026-11-11&period=day",
            ApiUrl.chart("https://h.example", d, Period.DAY))
    }

    @Test
    fun `mit schraegstrich am ende`() {
        assertEquals("https://h.example/api/chart?date=2026-11-11&period=week",
            ApiUrl.chart("https://h.example/", d, Period.WEEK))
    }

    @Test
    fun `mit pfad in der basis`() {
        assertEquals("https://h.example/heizung/api/chart?date=2026-11-11&period=day",
            ApiUrl.chart("https://h.example/heizung/", d, Period.DAY))
    }
}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `ApiUrl` implementieren** — Schrägstriche am Ende der Basis entfernen, dann `"$base/api/chart?date=$date&period=${period.name.lowercase()}"`.

- [ ] **Step 4: Tests für `HttpChartApi` mit MockWebServer schreiben**

```kotlin
class ChartApiTest {
    private val server = MockWebServer()

    @Test
    fun `holt und parst die antwort`() = runTest {
        server.enqueue(MockResponse().setBody("""[[1731250800,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,1,0,1,0,0,0,0,1,1,1]]"""))
        val api = HttpChartApi(baseUrl = { server.url("/").toString().trimEnd('/') })
        val rows = api.fetch(LocalDate.of(2026, 11, 11), Period.DAY)
        assertEquals(1, rows.size)
        assertEquals(1.0, rows[0].values[MetricId.KESSEL_RL])
        val request = server.takeRequest()
        assertEquals("/api/chart?date=2026-11-11&period=day", request.path)
    }

    @Test
    fun `http-fehler wird zur exception mit status`() = runTest {
        server.enqueue(MockResponse().setResponseCode(502))
        val api = HttpChartApi(baseUrl = { server.url("/").toString().trimEnd('/') })
        val error = runCatching { api.fetch(LocalDate.of(2026, 11, 11), Period.DAY) }.exceptionOrNull()
        assertTrue(error is ChartApiException)
        assertEquals(502, (error as ChartApiException).status)
    }
}
```

- [ ] **Step 5: `HttpChartApi` implementieren** — `withContext(Dispatchers.IO)`, `Request.Builder().url(...)`, Timeout 15 s, Body im Speicher lesen (maximal 8 MB, darüber `ChartApiException`), `ChartJson.parse`. Fehlerfälle in `class ChartApiException(message: String, val status: Int? = null)` übersetzen.

- [ ] **Step 6: Tests laufen lassen** — Expected: PASS.

- [ ] **Step 7: Commit** — `git commit -m "feat(android): HTTP-Client für die Chart-API"`

---

### Task 5: Sichtbarer Zeitausschnitt (Wischen, Zoomen, Beschriftung)

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/data/TimeWindow.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/data/TimeWindowTest.kt`

**Interfaces:**
- Consumes: `Period`, `ChartRow`.
- Produces:
  - `data class ViewWindow(val startSec: Long, val endSec: Long)`
  - `object TimeWindow { fun of(rows: List<ChartRow>): ViewWindow?; fun pan(window: ViewWindow, deltaSec: Long, bounds: ViewWindow): ViewWindow; fun zoom(window: ViewWindow, factor: Double, anchorSec: Long, bounds: ViewWindow): ViewWindow; fun tickLabels(window: ViewWindow, period: Period, zone: ZoneId): List<Pair<Long, String>> }`

- [ ] **Step 1: Tests schreiben**

```kotlin
class TimeWindowTest {
    private val zone = ZoneId.of("Europe/Berlin")
    private val bounds = ViewWindow(1_700_000_000, 1_700_086_400)

    @Test
    fun `wischen stoppt am rand`() {
        val w = ViewWindow(1_700_000_000, 1_700_043_200)
        assertEquals(w, TimeWindow.pan(w, -10_000, bounds).let { TimeWindow.pan(it, 0, bounds) })
        val left = TimeWindow.pan(w, -99_999_999, bounds)
        assertEquals(bounds.startSec, left.startSec)
        val right = TimeWindow.pan(w, 99_999_999, bounds)
        assertEquals(bounds.endSec, right.endSec)
        assertEquals(w.endSec - w.startSec, right.endSec - right.startSec)
    }

    @Test
    fun `zoomen haelt den ankerpunkt`() {
        val w = ViewWindow(0, 86_400)
        val z = TimeWindow.zoom(w, 0.5, anchorSec = 43_200, bounds = ViewWindow(0, 86_400))
        assertEquals(21_600, z.startSec)
        assertEquals(64_800, z.endSec)
    }

    @Test
    fun `zoom wird nicht kleiner als eine minute und nicht groesser als bounds`() {
        val tiny = TimeWindow.zoom(ViewWindow(0, 86_400), 0.0001, 43_200, ViewWindow(0, 86_400))
        assertTrue(tiny.endSec - tiny.startSec >= 60)
        val huge = TimeWindow.zoom(ViewWindow(0, 86_400), 100.0, 43_200, ViewWindow(0, 86_400))
        assertEquals(0, huge.startSec)
        assertEquals(86_400, huge.endSec)
    }

    @Test
    fun `tagsbeschriftung ist stundenweise in berliner zeit`() {
        val w = ViewWindow(1_700_000_000, 1_700_086_400) // 14.11.2023 23:13 UTC
        val labels = TimeWindow.tickLabels(w, Period.DAY, zone)
        assertTrue(labels.size in 4..8)
        assertTrue(labels.all { it.second.matches(Regex("""\d{2}:\d{2}""")) })
    }

    @Test
    fun `zeitumstellung ergibt 23-stunden-tag`() {
        // 30.03.2025, 00:00 lokal bis Folgetag 00:00 lokal
        val start = LocalDate.of(2025, 3, 30).atStartOfDay(zone).toEpochSecond()
        val end = LocalDate.of(2025, 3, 31).atStartOfDay(zone).toEpochSecond()
        assertEquals(23 * 3600L, end - start)
        val labels = TimeWindow.tickLabels(ViewWindow(start, end), Period.DAY, zone)
        assertEquals("00:00", labels.first().second)
        assertTrue(labels.none { it.second == "02:00" })
    }
}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `TimeWindow` implementieren** — `of(rows)` nimmt ersten und letzten Zeitstempel, `null` bei leerer Liste. `pan` klemmt die Breite bei und verschiebt innerhalb der Grenzen. `zoom` skaliert um den Anker, klemmt auf `[60 s, bounds-Breite]`. `tickLabels` wählt für `DAY` 4–8 runde Zeitpunkte (Stundenraster, mit `DateTimeFormatter.ofPattern("HH:mm")`), für `WEEK` je einen Punkt pro Tag (`"EEE"`, Locale.GERMAN).

- [ ] **Step 4: Tests laufen lassen** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(android): Zeitfenster für Wischen und Zoomen"`

---

### Task 6: Zustand der Oberfläche

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/ui/DashboardState.kt`, `.../ui/DashboardViewModel.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/ui/DashboardViewModelTest.kt`

**Interfaces:**
- Consumes: `ChartApi`, `Period`, `ChartRow`, `TimeWindow`, `ViewWindow`, `Catalog`, `MetricId`.
- Produces:
  - `data class DashboardState(val serverUrl: String?, val date: LocalDate, val period: Period, val tabIndex: Int, val hidden: Set<MetricId>, val rows: List<ChartRow>, val window: ViewWindow?, val loading: Boolean, val error: String?)`
  - `class DashboardViewModel(api: ChartApi, serverUrl: () -> String?) : ViewModel()` mit `val state: StateFlow<DashboardState>`, `fun setPeriod(Period)`, `fun previous()`, `fun next()`, `fun today()`, `fun selectTab(Int)`, `fun toggleSeries(MetricId)`, `fun pan(Long)`, `fun zoom(Double, Long)`, `fun resetZoom()`, `fun retry()`, `fun onServerUrlChanged()`

- [ ] **Step 1: Tests mit Fake-API schreiben**

```kotlin
class DashboardViewModelTest {
    private class FakeApi(var rows: List<ChartRow> = emptyList(), var error: Throwable? = null) : ChartApi {
        var calls = 0
        override suspend fun fetch(date: LocalDate, period: Period): List<ChartRow> {
            calls++
            error?.let { throw it }
            return rows
        }
    }

    private fun vm(api: ChartApi, url: String? = "https://h.example") =
        DashboardViewModel(api) { url }

    private fun sampleRows(n: Int) = (0 until n).map {
        ChartRow(
            timestampSec = 1_700_000_000 + it * 60L,
            values = MetricId.entries.associateWith { 20.0 + it },
        )
    }

    @Test
    fun `startet auf heute tag und puffer`() = runTest {
        val api = FakeApi(rows = sampleRows(3))
        val model = vm(api)
        advanceUntilIdle()
        assertEquals(0, model.state.value.tabIndex)
        assertEquals(Period.DAY, model.state.value.period)
        assertEquals(LocalDate.now(), model.state.value.date)
        assertEquals(3, model.state.value.rows.size)
    }

    @Test
    fun `ohne server-adresse wird nicht geladen und es gibt einen hinweis`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api, url = null)
        advanceUntilIdle()
        assertEquals(0, api.calls)
        assertNotNull(model.state.value.error)
    }

    @Test
    fun `zurueck blaettert um einen tag und laedt neu`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api)
        advanceUntilIdle()
        model.previous()
        advanceUntilIdle()
        assertEquals(LocalDate.now().minusDays(1), model.state.value.date)
        assertEquals(2, api.calls)
    }

    @Test
    fun `reiterwechsel laedt nicht neu`() = runTest {
        val api = FakeApi(rows = sampleRows(1))
        val model = vm(api)
        advanceUntilIdle()
        model.selectTab(2)
        advanceUntilIdle()
        assertEquals(2, model.state.value.tabIndex)
        assertEquals(1, api.calls)
    }

    @Test
    fun `legende blendet eine serie aus`() = runTest {
        val model = vm(FakeApi(rows = sampleRows(1)))
        advanceUntilIdle()
        model.toggleSeries(MetricId.SPEICHER_1_KOPF)
        assertTrue(MetricId.SPEICHER_1_KOPF in model.state.value.hidden)
        model.toggleSeries(MetricId.SPEICHER_1_KOPF)
        assertFalse(MetricId.SPEICHER_1_KOPF in model.state.value.hidden)
    }

    @Test
    fun `fehler wird als text angezeigt und retry laedt erneut`() = runTest {
        val api = FakeApi(error = ChartApiException("kaputt"))
        val model = vm(api)
        advanceUntilIdle()
        assertNotNull(model.state.value.error)
        assertFalse(model.state.value.loading)
        api.error = null
        api.rows = sampleRows(2)
        model.retry()
        advanceUntilIdle()
        assertNull(model.state.value.error)
        assertEquals(2, model.state.value.rows.size)
    }

    @Test
    fun `leere antwort setzt fenster auf null`() = runTest {
        val model = vm(FakeApi(rows = emptyList()))
        advanceUntilIdle()
        assertNull(model.state.value.window)
    }
}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `DashboardViewModel` implementieren** — Start im `init` über `viewModelScope.launch`; `load()` in `Dispatchers.IO`, Ergebnis in `state.update { }`; Fehlertexte deutsch („Server nicht erreichbar", „Keine Server-Adresse hinterlegt"). `window` wird nach jedem Laden auf `TimeWindow.of(rows)` gesetzt, `hidden` bei Datums-/Zeitraumwechsel geleert.

- [ ] **Step 4: Tests laufen lassen** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(android): Zustandsmodell des Dashboards"`

---

### Task 7: Server-Adresse merken

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/data/SettingsStore.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/data/SettingsStoreTest.kt` (Instrumentierung nur, wenn nötig — sonst `ApiUrlTest`-Stil für die Normalisierung)

**Interfaces:**
- Consumes: nichts.
- Produces: `class SettingsStore(private val context: Context) { val serverUrl: Flow<String?>; suspend fun save(raw: String) }`, `object ServerUrl { fun normalize(raw: String): String? }` — `null`, wenn leer oder kein `http(s)://`.

- [ ] **Step 1: Test für die Normalisierung schreiben**

```kotlin
class ServerUrlTest {
    @Test fun `leer ergibt null`() { assertNull(ServerUrl.normalize("  ")) }
    @Test fun `ohne schema ergibt null`() { assertNull(ServerUrl.normalize("heizung.example")) }
    @Test fun `schraegstrich wird entfernt`() {
        assertEquals("https://h.example", ServerUrl.normalize(" https://h.example/ "))
    }
    @Test fun `http bleibt erlaubt`() {
        assertEquals("http://192.168.1.9:8000", ServerUrl.normalize("http://192.168.1.9:8000"))
    }
}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `ServerUrl` und `SettingsStore` implementieren** — DataStore (`preferencesDataStore(name = "heizung")`), Schlüssel `server_url`, `save` normalisiert vor dem Schreiben und ignoriert `null`.

- [ ] **Step 4: Tests laufen lassen** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(android): Server-Adresse speichern"`

---

### Task 8: Diagramm zeichnen

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/ui/chart/ChartScale.kt`, `.../ui/chart/ChartCanvas.kt`, `.../ui/SensorColors.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/ui/chart/ChartScaleTest.kt`

**Interfaces:**
- Consumes: `Catalog`, `TabSpec`, `MetricId`, `ChartRow`, `ViewWindow`.
- Produces:
  - `object ChartScale { fun range(values: List<Double?>, minSpan: Double): ClosedFloatingPointRange<Double>; fun yOf(value: Double, range: ClosedFloatingPointRange<Double>, top: Float, bottom: Float): Float }`
  - `@Composable fun ChartCanvas(spec: TabSpec, rows: List<ChartRow>, window: ViewWindow, hidden: Set<MetricId>, labels: List<Pair<Long, String>>, onPan: (Long) -> Unit, onZoom: (Double, Long) -> Unit, onReset: () -> Unit, modifier: Modifier)`
  - `object SensorColors { fun of(metric: MetricId): Color }`

- [ ] **Step 1: Tests für die Skala schreiben**

```kotlin
class ChartScaleTest {
    @Test fun `leere werte ergeben einen sinnvollen bereich`() {
        val r = ChartScale.range(emptyList(), minSpan = 5.0)
        assertTrue(r.endInclusive > r.start)
    }
    @Test fun `konstante linie bekommt mindestspanne`() {
        val r = ChartScale.range(listOf(40.0, 40.0, 40.0), minSpan = 5.0)
        assertEquals(5.0, r.endInclusive - r.start, 0.001)
        assertTrue(r.start < 40.0 && r.endInclusive > 40.0)
    }
    @Test fun `nulls werden ignoriert`() {
        val r = ChartScale.range(listOf(null, 10.0, null, 30.0), minSpan = 1.0)
        assertTrue(r.start <= 10.0 && r.endInclusive >= 30.0)
    }
    @Test fun `ausreisser sprengen den bereich nicht unbegrenzt`() {
        val r = ChartScale.range(listOf(1.0, 2.0, 3.0, 1000.0), minSpan = 1.0)
        assertTrue(r.endInclusive <= 1200.0)
        assertEquals(1.0, r.start, 0.001)
    }
    @Test fun `y wert liegt zwischen oben und unten`() {
        val r = 0.0..100.0
        assertEquals(0f, ChartScale.yOf(100.0, r, top = 0f, bottom = 200f))
        assertEquals(200f, ChartScale.yOf(0.0, r, top = 0f, bottom = 200f))
    }
}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `ChartScale` implementieren** — Bereich aus Min/Max der endlichen Werte, um `minSpan` aufgeweitet, auf ganze Zahlen gerundet; `yOf` linear, geklemmt.

- [ ] **Step 4: `SensorColors` anlegen** — feste Farben je Metrik, dunkles Schema: Speicher 1–5 `#F472B6`, `#4EA1FF`, `#6EE7B7`, `#FACC15`, `#C084FC`; Außen `#9CA3AF`; Raum `#FB923C`; Vor-/Rücklauf `#4EA1FF`/`#F472B6`; Kessel `#F87171`; Solar `#FACC15`; Drehzahlen `#6EE7B7`; Digitalbänder `#34D399` bei 30 % Deckkraft.

- [ ] **Step 5: `ChartCanvas` bauen** — Aufteilung von oben nach unten: Temperaturbereich (mindestens 45 % der Höhe, y-Beschriftung rechts, Gitter alle 25 %), danach je eine Zeile für `spec.rows` (3–4 dp Abstand, eigene 0-bis-Max-Skala, keine Achsenbeschriftung), danach je eine Zeile für `spec.digital` (Stufenlinie `hv`, gefüllt bis zur Grundlinie), unten Platz für `labels`. Gesten über `pointerInput`: `detectTransformGestures` → `onZoom` mit Faktor und Anker, `detectDragGestures` → `onPan` mit `deltaX` umgerechnet in Sekunden, `detectTapGestures(onDoubleTap = { onReset() })`.

- [ ] **Step 6: Bauen** — Run: `./gradlew :app:assembleDebug`. Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 7: Commit** — `git commit -m "feat(android): Canvas-Renderer für die Diagramme"`

---

### Task 9: Hauptbildschirm mit Reitern und Legende

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/ui/DashboardScreen.kt`, `.../ui/Legend.kt`, `.../ui/theme/Theme.kt`
- Modify: `android/app/src/main/java/de/zwotzie/heizung/MainActivity.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/ui/LegendStateTest.kt`

**Interfaces:**
- Consumes: `DashboardViewModel`, `DashboardState`, `Catalog`, `ChartCanvas`, `SensorColors`, `SettingsStore`.
- Produces: `@Composable fun DashboardScreen(state: DashboardState, onEvent: (DashboardEvent) -> Unit)`, `sealed interface DashboardEvent { data class SetPeriod(Period); object Previous; object Next; object Today; data class SelectTab(Int); data class ToggleSeries(MetricId); data class Pan(Long); data class Zoom(Double, Long); object ResetZoom; object Retry; object OpenSettings }`, `@Composable fun LegendChips(spec: TabSpec, hidden: Set<MetricId>, onToggle: (MetricId) -> Unit)`, `data class LegendEntry(val metric: MetricId, val label: String, val color: Color)`, `object LegendEntries { fun of(spec: TabSpec): List<LegendEntry> }`

- [ ] **Step 1: Test für die Legendenreihen schreiben**

```kotlin
class LegendStateTest {
    @Test fun `legende zeigt temperaturen dann zeilen dann digitale signale`() {
        val entries = LegendEntries.of(Catalog.tabs[1]) // Solar
        assertEquals(Catalog.tabs[1].temperatures.first(), entries.first().metric)
        assertEquals(Catalog.tabs[1].digital.first(), entries.last().metric)
        assertEquals(Catalog.tabs[1].temperatures.size + Catalog.tabs[1].rows.size + Catalog.tabs[1].digital.size, entries.size)
    }
    @Test fun `jeder eintrag hat farbe und anzeigenamen`() {
        LegendEntries.of(Catalog.tabs[0]).forEach {
            assertTrue(it.label.isNotBlank())
            assertNotEquals(Color.Unspecified, it.color)
        }
    }
}
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `LegendEntries` (in `Legend.kt`) und `LegendChips` bauen** — `LegendChips` als `FlowRow` mit 4 dp Abstand; ausgeblendete Serien mit 35 % Deckkraft; Chip-Höhe mindestens 32 dp (Fingergröße).

- [ ] **Step 4: `DashboardScreen` bauen** — `Scaffold` mit `TopAppBar` (Titel „Heizung", Untertitel Datum als `EEE, d. MMM` auf Deutsch, Aktion: Einstellungen, Aktion: neu laden), darunter Zeile mit `SegmentedButton` Tag/Woche und ◀ · „Heute" · ▶, darunter `PrimaryTabRow` mit vier Reitern, darunter `ChartCanvas` mit `Modifier.weight(1f)`, darunter `LegendChips`. Zustände: `loading` → `LinearProgressIndicator` über dem Diagramm; `error` → Text plus Knopf „Erneut versuchen"; leere Daten → „Keine Daten für diesen Tag"; fehlende Adresse → „Server-Adresse fehlt" plus Knopf.

- [ ] **Step 5: Theme und Icon anlegen, `MainActivity` verdrahten** — dunkles Farbschema (`background #000000`, `surface #0C0C0C`, `onSurface #DFDFDF`, Akzent `#6EA8FE`), Statusleiste dunkel, `enableEdgeToEdge()`; adaptives Icon unter `res/mipmap-anydpi-v26/ic_launcher.xml` mit Hintergrund `#0C0C0C` und einer schlichten Thermometer-Silhouette als Vordergrund-Vektor (`res/drawable/ic_launcher_foreground.xml`, Farbe `#6EA8FE`); `MainActivity` erzeugt `SettingsStore`, `HttpChartApi`, `DashboardViewModel` und zeigt `DashboardScreen`.

- [ ] **Step 6: Bauen** — Run: `./gradlew :app:assembleDebug`. Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 7: Commit** — `git commit -m "feat(android): Hauptbildschirm mit Reitern und Legende"`

---

### Task 10: Einstellungen und erster Start

**Files:**
- Create: `android/app/src/main/java/de/zwotzie/heizung/ui/SettingsScreen.kt`
- Modify: `android/app/src/main/java/de/zwotzie/heizung/MainActivity.kt`, `.../ui/DashboardScreen.kt`
- Test: `android/app/src/test/java/de/zwotzie/heizung/ui/SettingsValidationTest.kt`

**Interfaces:**
- Consumes: `ServerUrl`, `SettingsStore`, `ChartApi`.
- Produces: `@Composable fun SettingsScreen(current: String?, onSave: (String) -> Unit, onClose: () -> Unit, onTest: suspend (String) -> Result<Int>)`, `object SettingsValidation { fun messageFor(raw: String): String? }`

- [ ] **Step 1: Test für die Eingabeprüfung schreiben**

```kotlin
class SettingsValidationTest {
    @Test fun `leer ist ein fehler`() { assertNotNull(SettingsValidation.messageFor("")) }
    @Test fun `ohne https oder http ist ein fehler`() {
        assertNotNull(SettingsValidation.messageFor("heizung.example"))
    }
    @Test fun `gueltige adresse ergibt keine meldung`() {
        assertNull(SettingsValidation.messageFor("https://heizung.example/"))
    }
}
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen.**

- [ ] **Step 3: `SettingsValidation` und `SettingsScreen` bauen** — Textfeld mit Tastaturtyp URI, Hinweis auf `https://`, Knopf „Verbindung testen" (ruft `fetch` für heute, zeigt „OK, 1440 Zeilen" oder die Fehlermeldung), Knopf „Speichern" (deaktiviert bei Fehler), Zurück-Pfeil.

- [ ] **Step 4: Ersten Start verdrahten** — Ist `serverUrl` leer, zeigt `MainActivity` nach dem Start `SettingsScreen` statt des Dashboards; nach dem Speichern lädt das Dashboard.

- [ ] **Step 5: Bauen und Tests** — Run: `./gradlew :app:testDebugUnitTest :app:assembleDebug`. Expected: PASS, `BUILD SUCCESSFUL`.

- [ ] **Step 6: Commit** — `git commit -m "feat(android): Einstellungen für die Server-Adresse"`

---

### Task 11: Bauen in GitHub Actions

**Files:**
- Create: `.github/workflows/android.yml`
- Modify: `android/app/build.gradle.kts` (Signierung), `README.md` (Abschnitt „Android-App")

**Interfaces:**
- Consumes: das Gradle-Projekt.
- Produces: Workflow „Android" mit Build auf Push und Release auf Tag `app-v*`.

- [ ] **Step 1: Signierkonfiguration in `app/build.gradle.kts` ergänzen**

Liest `HEIZUNG_KEYSTORE_PATH`, `HEIZUNG_KEYSTORE_PASSWORD`, `HEIZUNG_KEY_ALIAS`, `HEIZUNG_KEY_PASSWORD`; sind alle gesetzt, `signingConfigs.create("release")`, sonst `signingConfig = signingConfigs.getByName("debug")`. `buildTypes.release` nutzt sie, `isMinifyEnabled = false`.

- [ ] **Step 2: Workflow schreiben**

```yaml
name: Android
on:
  push:
    branches: ["**"]
    tags: ["app-v*"]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: android } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "17" }
      - uses: android-actions/setup-android@v3
      - name: Version aus dem Tag
        id: v
        run: |
          echo "code=$(git rev-list --count HEAD)" >> "$GITHUB_OUTPUT"
          echo "name=${GITHUB_REF_NAME#app-v}" >> "$GITHUB_OUTPUT"
      - name: Tests
        run: ./gradlew :app:testDebugUnitTest
      - name: Debug-APK
        run: ./gradlew :app:assembleDebug -PappVersionCode=${{ steps.v.outputs.code }} -PappVersionName=${{ steps.v.outputs.name }}
      - uses: actions/upload-artifact@v4
        with: { name: app-debug, path: android/app/build/outputs/apk/debug/app-debug.apk }

  release:
    if: startsWith(github.ref, 'refs/tags/app-v')
    needs: build
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: android } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "17" }
      - uses: android-actions/setup-android@v3
      - name: Keystore entschlüsseln
        env: { KEYSTORE_B64: "${{ secrets.HEIZUNG_KEYSTORE_BASE64 }}" }
        run: |
          if [ -n "$KEYSTORE_B64" ]; then
            echo "$KEYSTORE_B64" | base64 -d > "$RUNNER_TEMP/heizung.jks"
            echo "HEIZUNG_KEYSTORE_PATH=$RUNNER_TEMP/heizung.jks" >> "$GITHUB_ENV"
          else
            echo "::warning::Kein Keystore-Secret gesetzt – die APK wird debug-signiert."
          fi
      - name: Release-APK bauen
        env:
          HEIZUNG_KEYSTORE_PASSWORD: ${{ secrets.HEIZUNG_KEYSTORE_PASSWORD }}
          HEIZUNG_KEY_ALIAS: ${{ secrets.HEIZUNG_KEY_ALIAS }}
          HEIZUNG_KEY_PASSWORD: ${{ secrets.HEIZUNG_KEY_PASSWORD }}
        run: |
          ./gradlew :app:assembleRelease -PappVersionCode=$(git rev-list --count HEAD) -PappVersionName=${GITHUB_REF_NAME#app-v}
      - uses: softprops/action-gh-release@v2
        with:
          files: android/app/build/outputs/apk/release/app-release.apk
          name: Heizung ${{ github.ref_name }}
```

- [ ] **Step 3: Keystore für den Menschen erzeugen**

```bash
keytool -genkeypair -v -keystore ~/heizung-release.jks -alias heizung \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Heizung, O=privat, C=DE"
base64 -i ~/heizung-release.jks | pbcopy
```

Anleitung für GitHub → Settings → Secrets and variables → Actions: `HEIZUNG_KEYSTORE_BASE64` (Inhalt der Zwischenablage), `HEIZUNG_KEYSTORE_PASSWORD`, `HEIZUNG_KEY_ALIAS` (`heizung`), `HEIZUNG_KEY_PASSWORD`.

- [ ] **Step 4: README ergänzen** — kurzer Abschnitt „Android-App": wo der Code liegt, wie ein Release entsteht (Tag `app-v1.0` pushen), wie man die APK installiert, welche Secrets nötig sind.

- [ ] **Step 5: Prüfen** — Run: `./gradlew :app:testDebugUnitTest` lokal, danach Push und im Actions-Lauf kontrollieren, dass `build` grün ist und das Artefakt `app-debug` existiert.

- [ ] **Step 6: Commit** — `git commit -m "ci(android): APK-Build und Release über GitHub Actions"`

---

### Task 12: Abschlussprüfung auf dem Gerät

**Files:** keine neuen Dateien.

**Interfaces:** Consumes alles Vorherige.

- [ ] **Step 1: Release bauen** — Tag `app-v1.0` anlegen und pushen, im Actions-Lauf warten, bis das Release mit `app-release.apk` erscheint.

- [ ] **Step 2: Installieren** — APK auf dem Handy laden, „Unbekannte Quellen" erlauben, installieren.

- [ ] **Step 3: Abnahme** — prüfen: Start landet auf Puffer/Tag; sieben Kurven und die y-Achse rechts sind lesbar; Reiter wechseln ohne Nachladen; ◀/▶ und „Heute" ändern Tag und laden; Wischen und Pinch ändern den Ausschnitt, Doppeltipp setzt zurück; Legenden-Chip blendet aus und wieder ein; Solar zeigt Strahlung und Drehzahl in eigenen Zeilen; Flugmodus → Fehlermeldung mit „Erneut versuchen"; Einstellungen → Adresse ändern → lädt neu.

- [ ] **Step 4: Ergebnis notieren** — Abweichungen als neue Aufgaben im Plan ergänzen oder als Issue festhalten.
