import logging
import requests
import rdflib
from rdflib.namespace import RDF
from bs4 import BeautifulSoup
from enum import Enum
from dateutil.parser import parse

class Company(object):

    def __init__(self, ico, rejstrik, firma, sidlo, zapis):
        self.ico = ico
        self.rejstrik = rejstrik
        self.firma = firma
        self.sidlo = sidlo
        self.zapis = zapis


class Sidlo(object):

    def __init__(self, stat, psc, okres, obec, castObce, mop, ulice, cisloPop, cisloOr):
        self.stat = stat
        self.psc = psc
        self.okres = okres
        self.obec = obec
        self.castObce = castObce
        self.mop = mop
        self.ulice = ulice
        self.cisloPop = cisloPop
        self.cisloOr = cisloOr


class Rejstrik(Enum):
    NR = 0
    OR = 1
    ROPS = 2
    RSVJ = 3
    RU = 4
    SR = 5


def loadIco(ico):
    #url_base = "https://wwwinfo.mfcr.cz/cgi-bin/ares/darv_vreo.cgi?ico="

    #r = requests.get(url_base + ico)
    #r.raise_for_status()

    base_dir = "/Users/alexandr.mansurov/Downloads/VYSTUP/DATA/"
    filename = base_dir + ico + ".xml"
    try:
        with open(filename, 'r') as file:
            soup = BeautifulSoup(file.read(), 'lxml-xml')
            vypis = soup.find('are:Vypis_VREO')
            if vypis is None:
                logging.warning("Chybi vypis pro " + str(ico))

            return vypis
    except:
        return None


def parseVypis(vypis):
    if vypis is None:
        return None

    udaje = vypis.find('are:Zakladni_udaje')
    rejstrik = Rejstrik[udaje.find('are:Rejstrik').text]
    firma = udaje.find('are:ObchodniFirma').text
    ico = udaje.find('are:ICO').text

    sidlo_ruian_ = udaje.find('are:ruianKod')
    if None != sidlo_ruian_:
        sidlo_ruian = sidlo_ruian_.text
    else:
        sidlo_ruian = None
    zapis = udaje.find('are:DatumZapisu').text

    sidlo = udaje.find('are:Sidlo')
    stat_ = sidlo.find('are:stat')
    if stat_ != None:
        stat = stat_.text
    else:
        stat = None

    psc_=sidlo.find('are:psc')
    if psc_ != None:
        psc = psc_.text
    else:
        psc = None
    okres_ = sidlo.find('are:okres')
    if None != okres_:
        okres = okres_.text
    else:
        okres = None
    obec_ = sidlo.find('are:obec')
    if obec_ != None:
        obec = obec_.text
    else:
        obec = None

    castObce_ = sidlo.find('are:castObce')
    if castObce_ != None:
        castObce = castObce_.text
    else:
        castObce = None
    mop_ = sidlo.find('are:mop')
    if None != mop_:
        mop = mop_.text
    else:
        mop = None
    ulice_ = sidlo.find('are:ulice')
    if None != ulice_:
        ulice = ulice_.text
    else:
        ulice = ""
    cisloPop_ = sidlo.find('are:cisloPop')
    if None != cisloPop_:
        cisloPop = cisloPop_.text
    else:
        cisloPop = ""
    cisloOr_ = sidlo.find('are:cisloOr')
    if None != cisloOr_:
        cisloOr = cisloOr_.text
    else:
        cisloOr = None
    sidlo = Sidlo(stat, psc, okres, obec, castObce, mop, ulice, cisloPop, cisloOr)

    c = Company(ico, rejstrik, firma, sidlo, zapis)
    c.ruian = sidlo_ruian
    return c


def triplifyCompany(company):
    g = rdflib.Graph()

    if company is None:
        return g

    gr = rdflib.Namespace('http://purl.org/goodrelations/v1#')
    schema = rdflib.Namespace('http://schema.org/')
    g.bind('gr', gr)
    g.bind('schema', schema)

    base_ns = 'http://data.eghuro.cz/resource/'
    ico_ns = base_ns + 'business-entity/'

    business = rdflib.URIRef(ico_ns + 'CZ' + company.ico)

    b1 = rdflib.BNode()

    if company.sidlo.cisloOr != None:
        addr_str = company.sidlo.ulice + " " + company.sidlo.cisloPop + "/" + company.sidlo.cisloOr
    else:
        addr_str = company.sidlo.ulice + " " + company.sidlo.cisloPop

    for t in [
        (business, RDF.type, gr.BusinessEntity),
        (business, RDF.type, schema.Organization),
        (business, gr.legalName, rdflib.Literal(company.firma, lang="cs")),
        (business, schema.legalName, rdflib.Literal(company.firma, lang="cs")),
        (business, schema.identifier, rdflib.Literal(company.ico)),

        (business, schema.address, b1),
        (b1, RDF.type, schema.PostalAddress),
        (b1, schema.postalCode, rdflib.Literal(company.sidlo.psc)),
        (b1, schema.addressLocality, rdflib.Literal(company.sidlo.obec, lang="cs")),
        (b1, schema.streetAddress, rdflib.Literal(addr_str, lang="cs")),
        (b1, schema.region, rdflib.Literal(company.sidlo.okres, lang="cs")),
        #(business, schema.member, .)
    ]:
        g.add(t)

    return g

if __name__ == '__main__':
    print(triplifyCompany(parseVypis(loadIco('27074358'))).serialize(format='turtle'))
