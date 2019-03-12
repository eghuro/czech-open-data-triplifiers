Triplifiers of various Czech open data sets
====

Python scripts to convert existing dumps into RDF. Currently, they are very ugly and rather experimental.

Remember to install dependencies from requirements.txt before running the scripts.

Register of contracts
--
Metadata in the Czech registry of contracts converted from XML dumps.
January 2018 dump used.
Source data format: XML
Links to data source:
 - https://smlouvy.gov.cz/stranka/otevrena-data
 - https://data.smlouvy.cz/dump_2018_01.xml

ARES - Czech register of companies
--
Dump used as source. Only companies referenced in contracts are being triplified.
Source data format: XML
Links to data source:
 - https://wwwinfo.mfcr.cz/ares/
 - https://wwwinfo.mfcr.cz/ares/ares_vreo_all.tar.gz

Czech national bank rate list
--
CNB service / archive used. Only dates referenced in contracts as contract date ("datum uzavreni smlouvy") are being triplified.
Source data format: CSV like
Links to data source:
 - http://www.cnb.cz/cs/financni_trhy/devizovy_trh/kurzy_devizoveho_trhu/denni_kurz.txt?date=<%d.%m.%Y>

Code list of country names
--
Source data format: CSV-like
Links to data source:
 - https://adisepo.mfcr.cz/adistc/adis/idpr_pub/epo2_info/rozhrani_ciselniku.faces

List of databox holders
--
Source data format: XML
Links to data source:
 - https://www.mojedatovaschranka.cz/sds/welcome.do?part=opendata
