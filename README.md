# Usenet no
Arbeidsrepo for utforskning av den norske delen av usenet 

## Installasjon  

Med [uv](https://docs.astral.sh/uv/#installation):  
`uv sync`

Med pip og venv:   
```
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Data
Dataen vi bruker i dette repoet kommer fra to kilder: Internet Archive og Nasjonalbibliotekets nettarkiv (NWA).
Fordi disse dataene kan inneholde personopplysninger, er ikke selve dataen delt her.
Det vi har er skript for å laste ned, ekstrahere og parse dataen fra internet archive, samt forskjellige skript for å analysere dataen fra begge arkiver.

Når dataen lastet ned og pakket ut antas følgene filstruktur:  
```
data/
├── internet_archive/
│   ├── zipped_data/       # Nedlastede .zip-filer fra archive.org (src/usenet_no/scrape.py)
│   ├── unzipped_data/     # Utpakkede .mbox-filer (src/usenet_no/parse.py)
│   └── utf_8_data/        # UTF-8-enkodede .mbox-filer (src/usenet_no/parse.py)
├── nwa_90s/
│   ├── zipped_data/       # .tar-filer fra Nasjonalbiblioteket
│   ├── unzipped_data/     # Utpakkede meldingsfiler (scripts/nwa_to_mbox.py)
│   └── utf_8_data/        # Konkatenerte .mbox-filer, UTF-8-enkodet (scripts/nwa_to_mbox.py)
└── hidden/                # Mappings fra epost og navn til hash-verdier (src/usenet_no/make_user_mapping.py)
```
(analyseskriptene bruker bare utf_8_data-undermappene)

## Kode 
I src/usenet_no/ ligger kodemoduler med kjernefunksjonalitet for å jobbe med mboxdata, i tillegg til koden for å laste ned usenetarkivet.
I scripts/ ligger enkeltstående skript for å lage lese gjennom arkivet og lage statistikk (feks telle antall meldinger per bruker). Output fra disse lagres i data/. 
I notebooks/ ligger jupyter notebooks for å visualisere og tolke resultatene fra scripts/data.

### Nedlasting og parsing av norske usenet (Internet Archive)
`scrape` henter ut og laster ned alle zip-filene fra `https://archive.org/download/usenet-no` (lagres i `data/internet_archive/zipped_data` by default)  
`parse` zipper opp og leser ut alle mbox-filene fra outputen produsert av scrape. Mboxfilene dekodes og enkodes til utf-8 og lagres til `decoded-data-dir` (default arg er `data/internet_archive/utf_8_data`)

Disse kan kjøres f.eks slik (i denne rekkefølgen)

Med uv:  
`uv run -m usenet_no.scrape`  
`uv run -m usenet_no.parse`

Eller uten (i venv e.l):  
`python -m usenet_no.scrape`  
`python -m usenet_no.parse` 

### Parsing av NWA-data
`nwa_to_mbox` pakker ut .tar-filer fra `data/nwa_90s/zipped_data`, og skriver konkatenerte .mbox-filer til `data/nwa_90s/utf_8_data`

### Pseudonymisering
For å telle statistikk over brukerdata, har vi laget en mapping fra epost og navn i klartekst, til hashede verdier.  
Disse mappingene brukes når vi teller antall poster per epost o.l, slik at vi kan ha datafilene lagret på github uten av det inneholder epost-adressene. 

Med uv:  
`uv run -m usenet_no.make_user_mapping`  
`uv run -m usenet_no.make_user_mapping --extend -i data/nwa_90s/utf_8_data`  


Eller uten (i venv e.l):  
`python -m usenet_no.make_user_mapping`  
`python -m usenet_no.make_user_mapping --extend -i data/nwa_90s/utf_8_data`


### Skript
- scripts/count_messages_per_group.py — teller antall meldinger per newsgroup (mbox-fil). Output: `data/messages_per_group_ia.csv` / `data/messages_per_group_nwa.csv`
- scripts/count_messages_per_user.py — teller antall meldinger per bruker (anonymisert med hash). Output: `data/messages_per_user_ia.csv` / `data/messages_per_user_nwa.csv`
- scripts/count_dates.py — teller antall meldinger per dato. Output: `data/date_count_ia.csv` / `data/date_count_nwa.csv`
- scripts/compare_ia_nwa_content.py — sammenligner meldingsinnhold mellom IA og NWA ved eksakt tekstmatch, per newsgroup. Output: `data/ia_nwa_content_comparison.csv`

Kjøres slik:
`uv run scripts/count_messages_per_group.py`
`uv run scripts/count_messages_per_user.py`
`uv run scripts/count_dates.py`
`uv run scripts/compare_ia_nwa_content.py`


## ePADD
ePADD er et program som med et grafisk brukergrensesnitt som lar deg utforske epost-arkiver. 
Siden usenet-arkivet er lagret som .mbox-filer, kan man utforske dette arkivet med ePADD.

Last ned .jar-fil fra https://github.com/ePADD/epadd/releases/   
(filnavn: epadd-standalone.jar) og flytt hit  

Du må ha java installert  
`java -jar epadd-standalone.jar`

### NB-epadd 
Les om NB-epadd her https://github.com/NationalLibraryOfNorway/epadd-nb 
(Krever uthenting av entiteter utenfor epadd, les mer i README i repoet)


## For utviklere

### Pre-commit
Installér pre-commit (første gang):
`uv run pre-commit install` 

Da kjøres pre-commit hooks fra .pre-commit-config.yaml hver gang du gjør en commit 

### Tester
Vi organiserer tester som reflekterer mappestrukturen i src/, men med én fil per funksjon som skal testes. 
Det vil si at på innerste nivå, vil en .py fil i src tilsvare en mappe i tests/, med en test_navn_på_funksjon.py-fil per funksjon i .py-fila i src. 

Kjør tester slik: 
`uv run pytest`
