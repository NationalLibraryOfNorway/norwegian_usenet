# Usenet no
Arbeidsrepo for utforskning av den norske delen av usenet 

## Installasjon osv av python-kode  

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

## For utviklere
Installér pre-commit (første gang):
`uv run pre-commit install` 

Da kjøres pre-commit hooks fra .pre-commit-config.yaml hver gang du gjør en commit 

