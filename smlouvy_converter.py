import ares_converter as converter
from bs4 import BeautifulSoup
import cnb_converter as cnb
from datetime import datetime
from functools import lru_cache
import gc
import logging
import rdflib
from rdflib import Literal
from rdflib.namespace import RDF, RDFS, XSD


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler()])

def enrich_company(ico):
    return converter.triplifyCompany(converter.parseVypis(converter.loadIco(ico)))

def convertDump(filename, ares=True, rates=True):
    g = rdflib.ConjunctiveGraph()
    ns = rdflib.Namespace('http://data.eghuro.cz/resource/contract-cz/')
    pc = rdflib.Namespace('http://purl.org/procurement/public-contracts#')
    ico = rdflib.Namespace('http://data.eghuro.cz/resource/contract-party/')
        # for SILK as well as separating possibly LQ data in contract register
        # from HQ reference data in ARES
    isds = rdflib.Namespace('http://data.eghuro.cz/resource/databox/')
    gr = rdflib.Namespace('http://purl.org/goodrelations/v1#')
    cur = rdflib.Namespace('https://www.xe.com/currency/')
    adms = rdflib.Namespace('http://www.w3.org/ns/adms#')
    dcterms = rdflib.Namespace('http://purl.org/dc/terms/')
    schema = rdflib.Namespace('http://schema.org/')
    foaf = rdflib.Namespace('http://xmlns.com/foaf/0.1/')
    rates = rdflib.Namespace('http://data.eghuro.cz/resource/rates/czk/')
    dcat = rdflib.Namespace('http://www.w3.org/ns/dcat#')

    g.bind('pc', pc)
    g.bind('ico', ico)
    g.bind('gr', gr)
    g.bind('adms', adms)
    g.bind('dcterms', dcterms)
    g.bind('schema', schema)
    g.bind('foaf', foaf)
    g.bind('dcat', dcat)

    icos = set()
    dates = set()

    for t in [
        (ns['#'], RDF.type, dcat.DataSet),
        (ns['#'], dcterms.title, Literal("Registr smluv", lang="cs")),
        (ns['#'], dcterms.description, Literal("Metadata zveřejněná v Registru smluv", lang="cs")),
        (ns['#'], RDFS.comment, Literal("Metadata zveřejněná v Registru smluv konvertovaná z dumpů", lang="cs")),
        (ns['#'], dcterms.publisher, rdflib.URIRef("https://eghuro.cz/#me")),
        (ns['#'], dcterms.source, rdflib.URIRef("https://smlouvy.gov.cz/stranka/otevrena-data")),
        (ns['#'], dcterms.rightsHolder, rdflib.URIRef("https://www.mvcr.cz/"))
    ]:
        g.add(t)

    logging.info("Loading " + filename)
    with open(filename, 'r') as dump:
        soup = BeautifulSoup(dump.read(), 'lxml-xml')
        logging.info("Parsing records")
        for zaznam in soup.find_all('zaznam'):
            if zaznam.platnyZaznam.text != "1":
                logging.warn('Neplatny zaznam')
                continue

            b0 = rdflib.BNode()
            b1 = rdflib.BNode()

            id = zaznam.identifikator.idSmlouvy.text
            try:
                for t in [
                    (ns[id], RDF.type, pc.Contract),
                    (ns[id], RDFS.label, Literal(zaznam.smlouva.predmet.text, lang='cs')),
                    (ns[id], dcterms.available, Literal(zaznam.casZverejneni.text, datatype=XSD.dateTime)),
                    (ns[id], dcterms.hasVersion, rdflib.URIRef(zaznam.odkaz.text)),
                    (ns[id], dcterms.identifier, Literal(zaznam.identifikator.idSmlouvy.text)),
                    (ns[id], dcterms.title, Literal(zaznam.smlouva.predmet.text, lang='cs')),
                    (ns[id], pc.startDate, Literal(zaznam.smlouva.datumUzavreni.text, datatype=XSD.date)),
                ]:
                    g.add(t)

                if None != zaznam.smlouva.subjekt.find('ico'):
                    x = ico["CZ"+zaznam.smlouva.subjekt.ico.text.strip().replace(' ', '')]
                    for t in [
                        (ns[id], pc.contractingAuthority, x),
                        (x, RDF.type, gr.BusinessEntity),
                        (x, RDF.type, schema.Organization),
                        (x, gr.legalName, rdflib.Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                        (x, schema.legalName, rdflib.Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                        (x, schema.identifier, rdflib.Literal(zaznam.smlouva.subjekt.ico.text.strip().replace(' ', ''))),
                        (x, schema.address, rdflib.Literal(zaznam.smlouva.subjekt.adresa.text, lang="cs"))
                    ]:
                        g.add(t)

                    if None != zaznam.smlouva.subjekt.find('datovaSchranka'):
                        g.add( (x, foaf.account, isds[zaznam.smlouva.subjekt.datovaSchranka.text]) )
                else:
                    logging.warning("Chybi ICO:\n" + str(zaznam))
                    if None != zaznam.smlouva.subjekt.find('nazev') and None != zaznam.smlouva.smluvniStrana.find('adresa'):
                        b3 = rdflib.BNode()
                        for t in [
                            (ns[id], pc.supplier, b2),
                            (b3, RDF.type, gr.BusinessEntity),
                            (b3, RDF.type, schema.Organization),
                            (b3, gr.legalName, Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                            (b3, schema.legalName, Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                            (b3, schema.address, Literal(zaznam.smlouva.subjekt.adresa.text, lang="cs")),
                        ]:
                            g.add(t)
                        if None != zaznam.smlouva.subjekt.find('datovaSchranka'):
                            g.add( (b3, foaf.account, isds[zaznam.smlouva.subjekt.datovaSchranka.text]) )

                if None != zaznam.smlouva.find('hodnotaBezDph'):
                    for t in [
                        (ns[id], pc.agreedPrice, b0),
                        (b0, RDF.type, gr.UnitPriceSpecification),
                        (b0, gr.hasCurrency, cur.czk),
                        (b0, gr.hasCurrencyValue, Literal(zaznam.smlouva.hodnotaBezDph.text)),
                        (b0, gr.valueAddedTaxIncluded, Literal("false", datatype=XSD.boolean)),
                        #(b0, dcterms.relation, rates[zaznam.smlouva.datumUzavreni.text])
                    ]:
                        g.add(t)
                    if rates:
                        dates.add(datetime.strptime(zaznam.smlouva.datumUzavreni.text, "%Y-%m-%d"))

                if None != zaznam.smlouva.find('hodnotaVcetneDph'):
                    for t in [
                        (ns[id], pc.agreedPrice, b1),
                        (b1, RDF.type, gr.UnitPriceSpecification),
                        (b1, gr.hasCurrency, cur.czk),
                        (b1, gr.hasCurrencyValue, Literal(zaznam.smlouva.hodnotaVcetneDph.text)),
                        (b1, gr.valueAddedTaxIncluded, Literal("true", datatype=XSD.boolean)),
                        #(b1, dcterms.relation, rates[zaznam.smlouva.datumUzavreni.text])
                    ]:
                        g.add(t)
                    if rates:
                        dates.add(datetime.strptime(zaznam.smlouva.datumUzavreni.text, "%Y-%m-%d"))

                if None != zaznam.smlouva.find('cisloSmlouvy'):
                    g.add( (ns[id], adms.identifier, Literal(zaznam.smlouva.cisloSmlouvy.text)) )

                if None != zaznam.smlouva.smluvniStrana.find('ico'):
                    x = ico[zaznam.smlouva.smluvniStrana.ico.text.strip().replace(' ', '')]
                    for t in [
                        (ns[id], pc.supplier, x),
                        (x, RDF.type, gr.BusinessEntity),
                        (x, RDF.type, schema.Organization),
                        (x, gr.legalName, rdflib.Literal(zaznam.smlouva.smluvniStrana.nazev.text, lang="cs")),
                        (x, schema.legalName, rdflib.Literal(zaznam.smlouva.smluvniStrana.nazev.text, lang="cs")),
                        (x, schema.identifier, rdflib.Literal(zaznam.smlouva.smluvniStrana.ico.text.strip().replace(' ', '')))
                    ]:
                        g.add(t)

                    if None != zaznam.smlouva.smluvniStrana.find('adresa'):
                        g.add( (x, schema.address, rdflib.Literal(zaznam.smlouva.smluvniStrana.adresa.text, lang="cs")) )

                    if None != zaznam.smlouva.smluvniStrana.find('datovaSchranka'):
                        g.add( (x, foaf.account, isds[zaznam.smlouva.smluvniStrana.datovaSchranka.text]) )
                else:
                    if zaznam.smlouva.smluvniStrana.nazev.text.startswith('Údaj není veřejný') or \
                       zaznam.smlouva.smluvniStrana.nazev.text.startswith('Fyzická osoba - občan') or \
                       zaznam.smlouva.smluvniStrana.nazev.text.startswith('Obchodní tajemství'):
                        logging.warning("Údaj není veřejný\n" + str(zaznam))
                    elif None != zaznam.smlouva.smluvniStrana.find('adresa') or None != zaznam.smlouva.smluvniStrana.find('datovaSchranka'):
                        b2 = rdflib.BNode()
                        for t in [
                            (ns[id], pc.supplier, b2),
                            (b2, RDF.type, gr.BusinessEntity),
                            (b2, RDF.type, schema.Organization),
                            (b2, gr.legalName, Literal(zaznam.smlouva.smluvniStrana.nazev.text, lang="cs")),
                            (b2, schema.legalName, Literal(zaznam.smlouva.smluvniStrana.nazev.text, lang="cs")),
                            (b2, schema.address, Literal(zaznam.smlouva.smluvniStrana.adresa.text, lang="cs")),
                        ]:
                            g.add(t)
                        if None != zaznam.smlouva.smluvniStrana.find('datovaSchranka'):
                            g.add( (b2, foaf.account, isds[zaznam.smlouva.smluvniStrana.datovaSchranka.text]) )
                    else:
                        logging.warning('Nedostatečná identifikace smluvní strany:' + str(zaznam.smlouva.smluvniStrana))

                for priloha in zaznam.find_all('priloha'):
                    g.add((ns[id], pc.attachment, rdflib.URIRef(priloha.odkaz.text)))

                if ares:
                    for ico_record in zaznam.find_all('ico'):
                        icos.add(ico_record.text.strip().replace(' ', ''))
            except:
                logging.exception("Error\n"+str(zaznam))
                raise
    if ares:
        base_ns = 'http://data.eghuro.cz/resource/'
        ico_ns = base_ns + 'business-entity/'
        ico = rdflib.URIRef(ico_ns)
        for t in [
            (ico, RDF.type, dcat.DataSet),
            (ico, dcterms.title, Literal("ARES", lang="cs")),
            (ico, dcterms.description, Literal("Otevřená data v ARES", lang="cs")),
            (ico, RDFS.comment, Literal("Informace o osobách zapsaných v České republice ve veřejných rejstřících podle § 7 zákona č. 304/2013 Sb., o veřejných rejstřících právnických a fyzických osob, ve znění pozdějších předpisů", lang="cs")),
            (ico, dcterms.publisher, rdflib.URIRef("https://eghuro.cz/#me")),
            (ico, dcterms.source, rdflib.URIRef("https://wwwinfo.mfcr.cz/ares/ares_opendata.html.cz")),
            (ico, dcterms.rightsHolder, rdflib.URIRef("https://www.mfcr.cz/"))
        ]:
            g.add(t)
        for ico in icos:
            g.parse(data=enrich_company(ico).serialize(format="turtle"), format="turtle")
    if rates:
        g.parse(data=cnb.getRateGraph(dates).serialize(format="turtle"), format="turtle")
    return g

if __name__ == '__main__':
    convertDump('dump_2018_01.xml', ares=True, rates=True).serialize(format='turtle', destination='contracts.ttl')
