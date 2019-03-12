import csv
from decimal import Decimal
import logging
import requests
import rdflib
from rdflib import Literal
from rdflib.namespace import RDF, RDFS, XSD
import uuid

def getDecimal(text):
    if len(text) > 0:
        text = str(text)
        if " " in text:
            text = text.replace(" ", "")
        if "," in text:
            text = text.replace(",", ".")
        if text == '-':
            return Decimal(0.0)
        return Decimal(text)
    else:
        return Decimal(0.0)


def parseRateList(rates):
    loaded_ratelist = dict()
    for line in rates.split('\n')[2:]:
        record = line.split('|')
        if (record != []) and (record != ['']):
            #merge translated list into string and then convert to float and divide by amount
            loaded_ratelist[record[3]] = getDecimal(record[-1]) / getDecimal(record[2])
    loaded_ratelist['CZK'] = Decimal(1.0)
    return loaded_ratelist


def loadRateList(date):
    url_base = "http://www.cnb.cz/cs/financni_trhy/devizovy_trh/kurzy_devizoveho_trhu/denni_kurz.txt?date="
    url = url_base + date.strftime("%d.%m.%Y")
    r = requests.get(url)
    r.raise_for_status()
    return parseRateList(r.text)


def createCubeHeader(g):
    ns = rdflib.Namespace('http://data.eghuro.cz/resource/rates/')
    qb = rdflib.Namespace('http://purl.org/linked-data/cube#')
    sdmxAttribute = rdflib.Namespace('http://purl.org/linked-data/sdmx/2009/attribute#')
    sdmxDimension = rdflib.Namespace('http://purl.org/linked-data/sdmx/2009/dimension#')
    dcat = rdflib.Namespace('http://www.w3.org/ns/dcat#')
    dcterms = rdflib.Namespace('http://purl.org/dc/terms/')


    g.bind('qb', qb)
    g.bind('sdmx-attribute', sdmxAttribute)
    g.bind('sdmx-dimension', sdmxDimension)
    g.bind('dcat', dcat)
    g.bind('dcterms', dcterms)

    b1 = rdflib.BNode()
    b2  = rdflib.BNode()
    b3 = rdflib.BNode()
    b4 = rdflib.BNode()

    rat = ns.conversionRate

    for t in [
        (ns.dsd, RDF.type, qb.DataStructureDefinition),
        (ns.dsd, qb.component, b1),
        (b1, qb.dimension, sdmxDimension.currency),
        (b1, qb.order, Literal(1)),
        (ns.dsd, qb.component, b2),
        (b2, qb.dimension, sdmxDimension.refPeriod),
        (b2, qb.order, Literal(2)),
        (ns.dsd, qb.component, b4),
        (b4, qb.measure, ns.conversionRate),
        (ns.dsd, qb.component, b3),
        (b3, qb.attribute, sdmxAttribute.unitMeasure),
        (b3, qb.componentRequired, Literal("true", datatype=XSD.boolean)),
        (b3, qb.componentAttachment, qb.DataSet),

        (ns.rate, RDF.type, qb.DataSet),
        (ns.rate, RDFS.label, Literal("Kurzy devizového trhu", lang="cs")),
        (ns.rate, qb.structure, ns.dsd),
        (ns.rate, dcterms.title, Literal("Kurzy devizového trhu", lang="cs")),
        (ns.rate, dcterms.description, Literal("Denní kurzy devizového trhu vyhlašované Českou národní bankou", lang="cs")),
        (ns.rate, RDFS.comment, Literal("Denní kurzy devizového trhu vyhlašované Českou národní bankou", lang="cs")),
        (ns.rate, dcterms.publisher, rdflib.URIRef("http://eghuro.cz/#me")),
        (ns.rate, dcterms.source, rdflib.URIRef("http://www.cnb.cz/cs/financni_trhy/devizovy_trh/kurzy_devizoveho_trhu")),
        (ns.rate, dcterms.rightsHolder, rdflib.URIRef("http://www.cnb.cz")),

        (ns.sliceByDate, RDF.type, qb.SliceKey),
        (ns.sliceByDate, RDFS.label, Literal("Denní kurzovní lístek", lang="cs")),
        (ns.sliceByDate, RDFS.comment, Literal("Kurzy měn k danému fixnímu dni", lang="cs")),
        (ns.sliceByDate, qb.componentProperty, sdmxDimension.refPeriod),
        (ns.rate, qb.slice, ns.sliceByDate)
    ]:
        g.add(t)


def triplifyRateList(rates, date, g):
    ns = rdflib.Namespace('http://data.eghuro.cz/resource/rates/')
    qb = rdflib.Namespace('http://purl.org/linked-data/cube#')
    sdmxDimension = rdflib.Namespace('http://purl.org/linked-data/sdmx/2009/dimension#')
    cur = rdflib.Namespace('https://www.xe.com/currency/')
    dat = rdflib.Namespace('http://reference.data.gov.uk/id/gregorian-day/')

    sliceIri = rdflib.URIRef('http://data.eghuro.cz/resource/rates/czk/'+date.strftime("%Y-%m-%d"))
    for p, o in [
        (RDF.type, qb.Slice),
        (qb.sliceStructure, ns.sliceByDate),
        (sdmxDimension.refPeriod, dat[date.strftime("%Y-%m-%d")])
    ]:
        g.add((sliceIri, p, o))

    for currency in rates.keys():
        observationIri = rdflib.URIRef('http://data.eghuro.cz/resource/rates/czk/'+currency.lower()+'/'+date.strftime("%Y-%m-%d"))
        for p, o in [
            (RDF.type, qb.Observation),
            (qb.dataSet, ns.rate),
            (sdmxDimension.currency, cur[currency]),
            (sdmxDimension.refPeriod, dat[date.strftime("%Y-%m-%d")]),
            (ns.conversionRate, Literal('{0:.3f}'.format(rates[currency]), datatype=XSD.decimal))
        ]:
            g.add((observationIri, p, o))
        g.add((sliceIri, qb.observation, observationIri))


def getRateGraph(dates):
    g = rdflib.ConjunctiveGraph()
    createCubeHeader(g)
    for d in dates:
        try:
            rates = loadRateList(d)
            triplifyRateList(rates, d, g)
        except:
            logging.getLogger(__name__).exception("Failed to fetch rates for " + d.strftime("%Y-%m-%d"))
    return g


def getCompleteHistory():
    import datetime
    begin = datetime.strptime("1991-01-01", "%Y-%m-%d")
    end = datetime.strptime("2018-12-31", '%Y-%m-%d')
    step = datetime.timedelta(days=1)
    list = []

    now = begin
    while now <= end:
        list.append(now)
        now += step

    return getRateGraph(list)

if __name__ == '__main__':
    from datetime import date
    #g = rdflib.Graph()
    #createCubeHeader(g)
    #rates = loadRateList(date.today())
    #triplifyRateList(rates, date.today(), g)
    print(getCompleteHistory().serialize(format="turtle"))
