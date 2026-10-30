# Schnellstart

Dies ist ein **Release Candidate für eine Testinstallation**, keine bereits
freigegebene Produktionsversion. Der Quellcode, ein installierbares Wheel,
Frontend-Dateien und Tests sind enthalten. Die genaue Testabdeckung steht in
`COMPATIBILITY.md` und `docs/testing.md`.

1. Datenbank, Medien und Konfiguration sichern; zuerst eine Testinstanz verwenden.
2. Das mitgelieferte Wheel in der Python-Umgebung von InvenTree installieren.
   Bei Docker die Wheel-Datei und den Eintrag in `plugins.txt` dauerhaft bereitstellen.
3. Plugin-Unterstützung sowie App-, URL- und UI-Integration einschalten. Das Plugin
   aktivieren, Migrationen und `collectstatic` in der Wartungsumgebung
   ausführen und anschließend Webserver und Worker neu starten. Details: `docs/installation.md`.
4. Für einen Test ohne API-Schlüssel `DEMO_ENABLED` aktivieren und Open Food Facts
   vorübergehend deaktivieren. Nach `4006381333931` suchen.
5. Unter InvenTree 1.5.6 das Plugin-Panel eines Teils/einer Kategorie oder das
   Dashboard-Widget öffnen. Unter 1.6.3 steht zusätzlich eine eigene Navigationsseite
   zur Verfügung.
6. Produkt prüfen, Felder auswählen, Vergleich erzeugen und Import ausdrücklich
   bestätigen. Beim erneuten Suchen muss das vorhandene Teil erkannt werden.
7. Demo deaktivieren und echte Anbieter konfigurieren. Deren Live-Zugriff muss noch
   in deiner Umgebung geprüft werden; kommerzielle Konten waren beim Bau nicht verfügbar.

EAN wird nicht automatisch zur IPN. MPN und Hersteller werden nicht als Lieferant
behandelt. CSV-Mengen erzeugen keinen Lagerbestand. Kategorien und Parametervorlagen
müssen bereits existieren. Bilder/PDFs werden nur nach Freigabe und mit zulässigen
Hostnamen heruntergeladen. GS1 benötigt einen konkreten API-Vertrag und ist noch
nicht live angebunden.
