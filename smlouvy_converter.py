import os
import ares_converter as converter
from bs4 import BeautifulSoup
import cnb_converter as cnb
from datetime import datetime
from functools import lru_cache
import logging
import rdflib
from rdflib import Literal
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.store import Store
from rdflib_sqlalchemy.store import SQLAlchemy
from sqlalchemy import create_engine


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler()])

def enrich_company(ico):
    return converter.triplifyCompany(converter.parseVypis(converter.loadIco(ico)))

def convertDump(filename, ares_flag, rates_flag):
    g = rdflib.ConjunctiveGraph()
    ns = rdflib.Namespace('http://data.eghuro.cz/resource/contract-cz/')
    pc = rdflib.Namespace('http://purl.org/procurement/public-contracts#')
    ico = rdflib.Namespace('http://data.eghuro.cz/resource/contract-party/')
        # for SILK as well as separating possibly LQ data in contract register
        # from HQ reference data in ARES
    isds = rdflib.Namespace('http://data.eghuro.cz/resource/databox/')
    gr = rdflib.Namespace('http://purl.org/goodrelations/v1#')
    cur = rdflib.Namespace('https://www.xe.com/currency/')
    #TODO: cur = rdflib.Namespace('http://data.eghuro.cz/resource/currency/')
    adms = rdflib.Namespace('http://www.w3.org/ns/adms#')
    dcterms = rdflib.Namespace('http://purl.org/dc/terms/')
    schema = rdflib.Namespace('http://schema.org/')
    foaf = rdflib.Namespace('http://xmlns.com/foaf/0.1/')
    rates = rdflib.Namespace('http://data.eghuro.cz/resource/rates/czk/')
    skos = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')

    g.bind('pc', pc)
    g.bind('ico', ico)
    g.bind('gr', gr)
    g.bind('adms', adms)
    g.bind('dcterms', dcterms)
    g.bind('schema', schema)
    g.bind('foaf', foaf)
    g.bind('skos', skos)

    icos = set()
    dates = set()

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
            b4 = rdflib.BNode()

            id = zaznam.identifikator.idSmlouvy.text
            try:
                for t in [
                    (ns[id], RDF.type, pc.Contract),
                    (ns[id], RDFS.label, Literal(zaznam.smlouva.predmet.text, lang='cs')),
                    (ns[id], dcterms.available, Literal(zaznam.casZverejneni.text, datatype=XSD.dateTime)),
                    (ns[id], dcterms.hasVersion, rdflib.URIRef(zaznam.odkaz.text)),
                    (ns[id], dcterms.identifier, Literal(zaznam.identifikator.idSmlouvy.text)), #ID zaznamu v registru smluv
                    (ns[id], dcterms.title, Literal(zaznam.smlouva.predmet.text, lang='cs')),
                    (ns[id], pc.startDate, Literal(zaznam.smlouva.datumUzavreni.text, datatype=XSD.date)),
                ]:
                    g.add(t)

                if None != zaznam.smlouva.schvalil:
                    for t in [
                        (b4, RDF.type, foaf.Person),
                        (b4, RDFS.label, Literal(zaznam.smlouva.schvalil.text)),
                        (ns[id], pc.contact, b4)
                        ]:
                            g.add(t)

                if None != zaznam.smlouva.subjekt.find('ico'):
                    # TODO: inconsistent with other parts of the script, remove CZ (data cleaned with ico-fixing LSL)
                    x = ico["CZ"+zaznam.smlouva.subjekt.ico.text.strip().replace(' ', '')]
                    for t in [
                        (ns[id], pc.contractingAuthority, x),
                        (x, RDF.type, gr.BusinessEntity),
                        (x, RDF.type, schema.Organization),
                        (x, gr.legalName, rdflib.Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                        (x, schema.legalName, rdflib.Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                        (x, schema.identifier, rdflib.Literal(zaznam.smlouva.subjekt.ico.text.strip().replace(' ', ''))),
                        (x, schema.address, rdflib.Literal(zaznam.smlouva.subjekt.adresa.text, lang="cs")),
                        (b4, foaf.member, x)
                    ]:
                        g.add(t)

                    if None != zaznam.smlouva.subjekt.find('datovaSchranka'):
                        g.add( (x, foaf.account, isds[zaznam.smlouva.subjekt.datovaSchranka.text]) )
                else:
                    logging.warning("Chybi ICO:\n" + str(zaznam))
                    if None != zaznam.smlouva.subjekt.find('nazev') and None != zaznam.smlouva.smluvniStrana.find('adresa'):
                        b3 = rdflib.BNode()
                        for t in [
                            (ns[id], pc.contractingAuthority, b3),
                            (b3, RDF.type, gr.BusinessEntity),
                            (b3, RDF.type, schema.Organization),
                            (b3, gr.legalName, Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                            (b3, schema.legalName, Literal(zaznam.smlouva.subjekt.nazev.text, lang="cs")),
                            (b3, schema.address, Literal(zaznam.smlouva.subjekt.adresa.text, lang="cs")),
                            (b4, foaf.member, b3)
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
                        (b0, dcterms.relation, rates[zaznam.smlouva.datumUzavreni.text])
                    ]:
                        g.add(t)
                    if rates_flag:
                        dates.add(datetime.strptime(zaznam.smlouva.datumUzavreni.text, "%Y-%m-%d"))

                if None != zaznam.smlouva.find('hodnotaVcetneDph'):
                    for t in [
                        (ns[id], pc.agreedPrice, b1),
                        (b1, RDF.type, gr.UnitPriceSpecification),
                        (b1, gr.hasCurrency, cur.czk),
                        (b1, gr.hasCurrencyValue, Literal(zaznam.smlouva.hodnotaVcetneDph.text)),
                        (b1, gr.valueAddedTaxIncluded, Literal("true", datatype=XSD.boolean)),
                        (b1, dcterms.relation, rates[zaznam.smlouva.datumUzavreni.text])
                    ]:
                        g.add(t)
                    if rates_flag:
                        dates.add(datetime.strptime(zaznam.smlouva.datumUzavreni.text, "%Y-%m-%d"))
                #TODO: nove
                #if None != zaznam.smlouva.find('ciziMena'):
                #    for t in [
                #        (ns[id], pc.agreedPrice, b1),
                #        (b1, RDF.type, gr.UnitPriceSpecification),
                #        (b1, gr.hasCurrency, cur[zaznam.smlouva.ciziMena.mena.text.lower()]),
                #        (b1, dcterms.relation, rates[zaznam.smlouva.datumUzavreni.text])
                #    ]:
                #        g.add(t)
                #    if rates_flag:
                #        dates.add(datetime.strptime(zaznam.smlouva.datumUzavreni.text, "%Y-%m-%d"))

                if None != zaznam.smlouva.find('cisloSmlouvy'):
                    g.add( (ns[id], adms.identifier, Literal(zaznam.smlouva.cisloSmlouvy.text)) )

                for strana in zaznam.smlouva.find_all('smluvniStrana'):
                    if None != strana.find('ico'):
                        a = strana.ico.text.strip().replace(' ', '')
                        if a.startswith("nar."):
                            logging.warning("Datum narozeni misto ICO")
                            x = rdflib.BNode()
                        elif a.startswith("ČAK") or a.startswith("ČKA"):
                            logging.warning("Jiny identifikator misto ICO")
                            x = rdflib.BNode()
                        else:
                            x = ico[a]
                        for t in [
                            (ns[id], pc.supplier, x),
                            (x, RDF.type, gr.BusinessEntity),
                            (x, RDF.type, schema.Organization),
                            (x, gr.legalName, rdflib.Literal(strana.nazev.text)),
                            (x, schema.legalName, rdflib.Literal(strana.nazev.text)),
                            (x, schema.identifier, rdflib.Literal(strana.ico.text.strip().replace(' ', '')))
                        ]:
                            g.add(t)

                        if None != strana.find('adresa'):
                            g.add( (x, schema.address, rdflib.Literal(strana.adresa.text)) )

                        if None != strana.find('datovaSchranka'):
                            g.add( (x, foaf.account, isds[strana.datovaSchranka.text]) )
                    else:
                        if strana.nazev.text.lower().startswith('údaj není veřejný') or \
                           strana.nazev.text.lower().startswith('fyzická osoba - občan') or \
                           strana.nazev.text.lower().startswith('obchodní tajemství'):
                            logging.warning("Údaj není veřejný\n" + str(zaznam))
                        else:
                            b2 = rdflib.BNode()
                            for t in [
                                (ns[id], pc.supplier, b2),
                                (b2, RDF.type, gr.BusinessEntity),
                                (b2, RDF.type, schema.Organization),
                                (b2, gr.legalName, Literal(strana.nazev.text)),
                                (b2, schema.legalName, Literal(strana.nazev.text)),
                            ]:
                                g.add(t)
                            if None != strana.find('adresa'):
                                g.add( (b2, schema.address, Literal(strana.adresa.text)) )
                            if None != strana.find('datovaSchranka'):
                                g.add( (b2, foaf.account, isds[strana.datovaSchranka.text]) )
                            if None == strana.find('adresa') and None == strana.find('datovaSchranka'):
                                logging.warning('Nedostatečná identifikace smluvní strany:' + str(strana))

                for priloha in zaznam.find_all('priloha'):
                    g.add((ns[id], pc.agreement, rdflib.URIRef(priloha.odkaz.text)))


                if ares_flag:
                    for ico_record in zaznam.find_all('ico'):
                        icos.add(ico_record.text.strip().replace(' ', ''))
            except:
                logging.exception("Error\n"+str(zaznam))
                raise
    logging.info("Serializing final graph of contracts")
    g.serialize(format='turtle', destination='/Users/alexandr.mansurov/workspace/DP+DIQ-playground/ares-stub/out/contracts.ttl')
    if ares_flag:
        logging.info("ARES")
        converter.prepare("rejstrik.ttl", "zeme.ttl")

        gg = rdflib.ConjunctiveGraph()
        for ico in icos:
            gg.parse(data=enrich_company(ico).serialize(format="turtle"), format="turtle")

        logging.info("Serializing final graph of ARES")
        gg.serialize(format="turtle", destination="/Users/alexandr.mansurov/workspace/DP+DIQ-playground/ares-stub/out/ares.ttl")
    if rates_flag:
        try:
            logging.info("Rates")
            #dburi = "sqlite:///%(here)s/development.sqlite" % {"here": os.getcwd()}
            #dburi = "sqlite:///Volumes/Data/triples.sqlite"
            #engine = create_engine(dburi)
            #ident = rdflib.URIRef("rates")
            #store = SQLAlchemy(identifier=ident, engine=engine)
            #h = rdflib.Graph(store, identifier=ident)
            #h.open(Literal(dburi), create=True)
            h = rdflib.Graph()
            ttl = cnb.getRateGraph(dates).serialize(format="turtle")
            #h.parse(data=ttl, format="turtle")
            h.serialize(destination="/Volumes/Data/rates.ttl", format="turtle")
            #try:
            #    h.close()
            #except:
            #    pass
        except:
            logging.exception("Failed to fetch rates, dates were: " + str(",".join([d.strftime("%Y-%m-%d") for d in dates])))
    #return g

if __name__ == '__main__':
    try:
        convertDump('dump_2018_01.xml', False, False)
    except:
        print("\a\a")
        raise
