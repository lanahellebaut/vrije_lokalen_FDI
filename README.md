# Vrije lokalen

Elke werkdag om 6u en om 12u (in de zomer 7u en 13u) haalt GitHub het TimeEdit-rooster op en bouwt het de pagina opnieuw. Daarna hoef je er niets meer aan te doen.

## Eenmalig opzetten (± 15 min)

1. **Repository aanmaken.** Ga op github.com naar *New repository*, kies een naam (bv. `vrije-lokalen`) en zet hem op **Public**. Voor een gratis account is dat nodig om GitHub Pages te kunnen gebruiken. De TimeEdit-link komt niet in de code, dus die blijft geheim.
2. **Bestanden uploaden.** Kies *Add file → Upload files* en sleep de inhoud van deze map erin, inclusief de map `.github`. Klik op *Commit changes*.
   - Zie je de map `.github` niet in je verkenner? Dan is hij verborgen. Maak hem in dat geval via *Add file → Create new file* aan met als naam `.github/workflows/update.yml` en plak de inhoud erin.
3. **TimeEdit-links toevoegen.** Ga naar *Settings → Secrets and variables → Actions → New repository secret*.
   - Name: `ICS_URLS`
   - Secret: de abonnementslink(s) uit TimeEdit, één per regel
4. **Pagina aanzetten.** Ga naar *Settings → Pages*, kies Source *Deploy from a branch*, Branch `main` en map `/docs`, en klik op *Save*.
5. **Eerste keer draaien.** Ga naar *Actions → Rooster bijwerken → Run workflow*. Na een minuut of twee staat de pagina online op `https://<jouw-gebruikersnaam>.github.io/vrije-lokalen/`. Die link geef je aan de studenten.

## Aanpassen

Alles staat in `config.json`:

- `dag_start` / `dag_einde`: welke uren meetellen
- `sluiting_activiteiten`: activiteiten die als "gebouw gesloten" getoond worden
- `aantal_dagen`: hoeveel dagen vooruit
- `lokaalnamen`: als je een andere naam wilt tonen, bv. `{"Auditorium 1. D1": "Auditorium 1"}`

Wil je een lokaal toevoegen of verwijderen? Pas dan het secret `ICS_URLS` aan.

## Goed om te weten

- Namen van docenten worden niet getoond. De naam van een activiteit zie je alleen als je met de muis over een grijs blok gaat.
- Als TimeEdit eens niet bereikbaar is, blijft de vorige versie van de pagina gewoon staan.
- Als het ophalen mislukt, stuurt GitHub een mail naar het account.
