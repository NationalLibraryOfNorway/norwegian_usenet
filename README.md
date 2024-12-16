# Usenet no
Arbeidsrepo for utforskning av den norske delen av usenet 

## Installasjon osv av python-kode  
Med pdm:  
`pdm install`

Med pip (med et venv e.l):   
`pip install .`

### Kjør moduler: 
Med pdm:  
`pdm run python -m usenet_no.scrape`  
`pdm run python -m usenet_no.parse`  

Eller uten (i venv e.l):  
`python -m usenet_no.scrape`  
`python -m usenet_no.parse`  


## Kjør opp epadd 
Last ned .jar-fil fra https://github.com/ePADD/epadd/releases/   
(filnavn: epadd-standalone.jar) og flytt hit  
Du må ha java installert  
`java -jar epadd-standalone.jar`
