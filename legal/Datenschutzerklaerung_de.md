# Datenschutzerklärung

**Anbieter:** Nazir Sultani, [vollständige Adresse], [E-Mail], sultani.de
**Stand:** April 2026

---

## 1. Allgemeines

Der Schutz Ihrer personenbezogenen Daten ist uns wichtig. Diese Datenschutzerklärung informiert Sie darüber, welche Daten im Zusammenhang mit dem Erwerb und der Nutzung der Software **WAPI** (erhältlich über sultani.de und wapi.sultani.de) verarbeitet werden, zu welchem Zweck und auf welcher Rechtsgrundlage.

Verantwortlicher im Sinne der DSGVO:

**Nazir Sultani**
[vollständige Adresse]
[E-Mail-Adresse]
sultani.de

---

## 2. Verarbeitung beim Kauf (über Lemon Squeezy)

### 2.1 Lemon Squeezy als Merchant of Record

Der Kauf von WAPI-Lizenzen wird über **Lemon Squeezy** (Lemon Squeezy, LLC) abgewickelt. Lemon Squeezy agiert als **Merchant of Record** und ist damit selbständig für die Zahlungsabwicklung, die steuerliche Compliance (inkl. EU-Mehrwertsteuer) und den Schutz Ihrer Zahlungsdaten verantwortlich.

Im Rahmen des Kaufvorgangs verarbeitet Lemon Squeezy insbesondere:
- Name und E-Mail-Adresse
- Rechnungsadresse
- Zahlungsdaten (Kreditkarte, PayPal etc.)

Lemon Squeezy handelt dabei als eigenständiger Verantwortlicher nach Art. 4 Nr. 7 DSGVO. Die Datenschutzrichtlinie von Lemon Squeezy finden Sie unter: https://www.lemonsqueezy.com/privacy

### 2.2 Übermittlung des Lizenzschlüssels

Nach erfolgtem Kauf übermittelt Lemon Squeezy uns per Webhook-Benachrichtigung folgende Daten:
- E-Mail-Adresse des Käufers
- Name des Käufers (sofern angegeben)
- Lizenzschlüssel

Diese Daten werden in unserer Lizenzdatenbank (gehostet auf Railway) gespeichert, um die Lizenzaktivierung zu ermöglichen.

**Rechtsgrundlage:** Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)

---

## 3. Verarbeitung bei der Lizenzaktivierung und -prüfung

### 3.1 Aktivierungsdaten

Bei der erstmaligen Aktivierung von WAPI auf Ihrem Gerät werden folgende Daten an unseren Server übermittelt:

| Datenkategorie | Inhalt | Zweck |
|---|---|---|
| Lizenzschlüssel | Ihr persönlicher Lizenzcode | Zuordnung zur Lizenz |
| Gerätekennung (instance_id) | SHA-256-Hash aus technischen Systemparametern (Gerätename, Prozessor, Architektur) | Erkennung des aktivierten Geräts |
| Gerätename | Hostname des Computers | Anzeige im Admin-Dashboard |
| App-Version | Versionsnummer von WAPI | Kompatibilitätsprüfung |
| IP-Adresse | Automatisch durch die Serveranfrage übermittelt | Protokollierung (Logs) |

**Zur Gerätekennung:** Die `instance_id` ist ein SHA-256-Hash und lässt **keine direkte Rückführung auf Ihre Person** zu. Es werden weder MAC-Adressen noch Hardware-Seriennummern übertragen.

**Rechtsgrundlage:** Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung – zur Bereitstellung des lizenzierten Produkts)

### 3.2 Periodische Lizenzprüfung

WAPI führt ca. alle **7 Tage** eine automatische Online-Prüfung durch, um die Gültigkeit Ihrer Lizenz zu verifizieren. Dabei werden Lizenzschlüssel und Gerätekennung übermittelt. Bei Nichterreichbarkeit des Servers bleibt WAPI weiterhin nutzbar (Offline-Toleranz).

**Rechtsgrundlage:** Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung – Lizenzschutz als Vertragsbestandteil)

---

## 4. Lokale Datenspeicherung

WAPI speichert lokal auf Ihrem Computer:
- Eine **Lizenzdatei** (`wapi_license.json`) mit Lizenzschlüssel, Gerätekennung, E-Mail-Adresse und Zeitstempel der letzten Prüfung
- Eine **Einstellungsdatei** (`wapi_settings.json`) mit Ihren App-Konfigurationen (Wasserzeichen-Einstellungen, Exportpfade etc.)

Diese Dateien liegen vollständig unter Ihrer Kontrolle und werden **nicht** an Dritte übermittelt, außer im Rahmen der in § 3 beschriebenen Aktivierungs- und Validierungsanfragen.

---

## 5. Hosting und Auftragsverarbeitung

Unser Lizenzserver ist bei **Railway** (Railway Corp., USA) gehostet. Railway verarbeitet dabei als Auftragsverarbeiter gemäß Art. 28 DSGVO personenbezogene Daten in unserem Auftrag. Die Datenverarbeitung findet in der EU/EEA oder den USA statt; Railway ist nach dem EU-US Data Privacy Framework zertifiziert.

Datenschutzinformationen von Railway: https://railway.app/legal/privacy

---

## 6. Speicherdauer

| Datenkategorie | Speicherdauer |
|---|---|
| Kundendaten (E-Mail, Name, Lizenzschlüssel) | Solange die Lizenz aktiv ist + gesetzliche Aufbewahrungsfristen (max. 10 Jahre für steuerlich relevante Daten) |
| Aktivierungsprotokolle | 12 Monate |
| Webhook-Logs | 90 Tage |

Nach Ablauf der Speicherdauer werden die Daten gelöscht oder anonymisiert.

---

## 7. Ihre Rechte

Sie haben nach der DSGVO folgende Rechte:

- **Auskunft** (Art. 15 DSGVO): Auskunft über die zu Ihrer Person gespeicherten Daten
- **Berichtigung** (Art. 16 DSGVO): Korrektur unrichtiger Daten
- **Löschung** (Art. 17 DSGVO): Löschung Ihrer Daten, sofern keine Aufbewahrungspflichten entgegenstehen
- **Einschränkung der Verarbeitung** (Art. 18 DSGVO)
- **Datenübertragbarkeit** (Art. 20 DSGVO)
- **Widerspruch** (Art. 21 DSGVO): Widerspruch gegen die Verarbeitung

Zur Ausübung Ihrer Rechte wenden Sie sich bitte an: [E-Mail-Adresse]

---

## 8. Beschwerderecht

Sie haben das Recht, sich bei einer Datenschutzaufsichtsbehörde zu beschweren. Die zuständige Behörde richtet sich nach Ihrem Wohnsitz. Eine Übersicht aller deutschen Aufsichtsbehörden finden Sie unter: https://www.bfdi.bund.de/DE/Infothek/Anschriften_Links/anschriften_links-node.html

---

## 9. Keine Weitergabe an Dritte

Wir geben Ihre personenbezogenen Daten **nicht** an Dritte weiter, außer:
- an Lemon Squeezy (Zahlungsabwicklung, s. § 2)
- an Railway (Hosting, s. § 5)
- wenn wir gesetzlich dazu verpflichtet sind

---

## 10. Cookies und Tracking

Die Website sultani.de und wapi.sultani.de sowie die WAPI-Software selbst verwenden **keine Tracking-Cookies** und **kein Analyse- oder Tracking-Tool** (kein Google Analytics o. Ä.).

---

> **Hinweis:** Diese Datenschutzerklärung ist ein Entwurf. Bitte von einem Rechtsanwalt oder Datenschutzbeauftragten prüfen lassen. Die markierten Platzhalter (Adresse, E-Mail) sind vor der Veröffentlichung zu vervollständigen.
