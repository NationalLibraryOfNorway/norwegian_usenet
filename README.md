# Usenet no
Arbeidsrepo for utforskning av den norske delen av usenet 

## Installasjon  

Med [uv](https://docs.astral.sh/uv/#installation):  
`uv sync`

Med pip og venv (med et venv e.l):   
```
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

### Kjør moduler: 
Med uv:  
`uv run -m usenet_no.scrape`  
`uv run -m usenet_no.parse`  

Eller uten (i venv e.l):  
`python -m usenet_no.scrape`  
`python -m usenet_no.parse` 

## Kjør opp epadd 
Last ned .jar-fil fra https://github.com/ePADD/epadd/releases/   
(filnavn: epadd-standalone.jar) og flytt hit  

Du må ha java installert  
`java -jar epadd-standalone.jar`

### NB-epadd 
Les om NB-epadd her https://github.com/NationalLibraryOfNorway/epadd-nb 
(Krever uthenting av entiteter utenfor epadd, les mer i README i repoet)


## Forklaring av moduler
`scrape` henter ut og laster ned alle zip-filene fra `https://archive.org/download/usenet-no`  
`parse` zipper opp og leser ut alle mbox-filene fra outputen produsert av scrape. Mboxfilene dekodes og enkodes til utf-8 og lagres til `decoded-data-dir` (default arg er `data/utf_8_data`)
Alle moduler som starter med `count` gjør forskjellig opptelling av poster i mboxfilene i `decoded-data-dir`. Output skrives til `data` 

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
