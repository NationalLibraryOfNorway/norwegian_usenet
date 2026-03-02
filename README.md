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
Dataen vi bruker i dette repo kommer fra archive.org sin versjon av norske usenet. 
Dette arkivet åpent på internett, men fordi disse dataene kan inneholde personopplysninger, er ikke selve dataen delt her. 
Det vi har er skript for å laste ned, ekstrahere og parse dataen, samt forskjellige skript for å analysere dataen.

## Kode 
I src/usenet_no/ ligger kodemoduler med kjernefunksjonalitet for å jobbe med mboxdata, i tillegg til koden for å laste ned usenetarkivet.
I scripts/ ligger enkeltstående skript for å lage lese gjennom arkivet og lage statistikk (feks telle antall meldinger per bruker). Output fra disse lagres i data/. 
I notebooks/ ligger jupyter notebooks for å visualisere og tolke resultatene fra scripts/data.

### Nedlasting og parsing av norske usenet
`scrape` henter ut og laster ned alle zip-filene fra `https://archive.org/download/usenet-no` (lagres i `data/zipped_data` by default) 
`parse` zipper opp og leser ut alle mbox-filene fra outputen produsert av scrape. Mboxfilene dekodes og enkodes til utf-8 og lagres til `decoded-data-dir` (default arg er `data/utf_8_data`)
`make_user_mapping` leser navn og epost-adresser fra alle meldingene i arkivet, og lager unike hash-verdier slik at vi kan lagre brukerstatistikk i repoet uten å dele navn og epost til enkeltpersoner

Disse kan kjøres f.eks slik (i denne rekkefølgen)

Med uv:  
`uv run -m usenet_no.scrape`  
`uv run -m usenet_no.parse`
`uv run -m usenet_no.make_user_mapping`  

Eller uten (i venv e.l):  
`python -m usenet_no.scrape`  
`python -m usenet_no.parse` 
`python -m usenet_no.make_user_mapping`  

### Skript
- `count_messages_per_group.py` — teller antall meldinger per news group (mbox-fil). Output: `data/messages_per_group.csv`
- `count_messages_per_user.py` — teller antall meldinger per bruker (anonymisert med hash). Output: `data/messages_per_user.csv`
- `count_dates.py` — teller antall meldinger per dato. Output: `data/date_count.csv`

Kjøres slik:
`uv run scripts/count_messages_per_group.py`
`uv run scripts/count_messages_per_user.py`
`uv run scripts/count_dates.py`


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
