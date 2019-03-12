import os
import csv
import logging
import requests
import rdflib
import uuid
from itertools import islice
from rdflib import Literal
from rdflib.namespace import RDF, XSD
from bs4 import BeautifulSoup
from enum import Enum
from dateutil.parser import parse

class Company(object):

    def __init__(self, ico, rejstrik, firma, sidlo, zapis, cinnosti):
        self.ico = ico
        self.rejstrik = rejstrik
        self.firma = firma
        self.sidlo = sidlo
        self.zapis = zapis
        self.cinnosti = cinnosti


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


class Member(object):

    def __init__(self, funkce, organ, adresa, statutar, dza, dvy):
        self.funkce = funkce
        self.organ = organ
        self.adresa = adresa
        self.statutar = statutar
        self.zapsan = dza
        self.vyskrtnut = dvy


class MemberFO(Member):

    def __init__(self, jmeno, prijmeni, funkce, organ, adresa, statutar, zapsan, vyskrtnut):
        Member.__init__(self, funkce, organ, adresa, statutar, zapsan, vyskrtnut)
        self.jmeno = jmeno
        self.prijmeni = prijmeni


class MemberPO(Member):

    def __init__(self, nazev, funkce, organ, adresa, statutar, zapsan, vyskrtnut, ico):
        Member.__init__(self, funkce, organ, adresa, statutar, zapsan, vyskrtnut)
        self.nazev = nazev
        self.ico = ico


class Rejstrik(Enum):
    NR = 0
    OR = 1
    ROPS = 2
    RSVJ = 3
    RU = 4
    SR = 5


class Forma(Enum):
   SRO = 0
   AS = 1
   VOS = 2
   KS = 3
   ZS = 4
   SE = 5


def prepare(rejstrik_out, zeme_out):
    g = rdflib.Graph()
    skos = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')
    g.bind('skos', skos)

    base_ns = 'http://data.eghuro.cz/resource/'
    ico_ns = base_ns + 'business-entity/'

    rejstrik_ns = base_ns + 'public-register/'
    rejstrik = rdflib.Namespace(rejstrik_ns)
    g.add((rdflib.URIRef(rejstrik_ns), RDF.type, skos.ConceptScheme))
    for r in [
        ('NR', 'Nadační rejstřík'),
        ('OR', 'Obchodní rejstřík'),
        ('ROPS', 'Rejstřík obecně prospěšných společností'),
        ('RSVJ', 'Rejstřík společenství vlastníků jednotek'),
        ('RU', 'Rejstřík ústavů'),
        ('SR', 'Spolkový rejstřík')
    ]:
        for t in [
            (rejstrik[r[0]], RDF.type, skos.Concept),
            (rejstrik[r[0]], skos.inScheme, rdflib.URIRef(rejstrik_ns)),
            (rejstrik[r[0]], skos.prefLabel, Literal(r[1], lang="cs"))
        ]:
            g.add(t)

    forma_ns = base_ns + 'organisation-type/'
    forma = rdflib.Namespace(forma_ns)
    g.add((rdflib.URIRef(forma_ns), RDF.type, skos.ConceptScheme))
    for f in Forma:
        g.add( (forma[str(f)], RDF.type, skos.Concept) )

    g.serialize(destination=rejstrik_out, format="turtle")

    g = rdflib.Graph()
    g.bind('skos', skos)
    zeme_iso_ns = base_ns + 'country/iso/'
    zeme_iso = rdflib.Namespace(zeme_iso_ns)
    zeme_ns = base_ns + 'country/'
    zeme = rdflib.Namespace(zeme_ns)
    zeme_eu_ns = base_ns + 'country/eu/'
    zeme_eu = rdflib.Namespace(zeme_eu_ns)
    for t in [
        (rdflib.URIRef(zeme_iso_ns), RDF.type, skos.ConceptScheme),
        (rdflib.URIRef(zeme_ns), RDF.type, skos.ConceptScheme),
        (rdflib.URIRef(zeme_eu_ns), RDF.type, skos.ConceptScheme),
        (zeme_eu['members'], RDF.type, skos.Collection)
    ]:
        g.add(t)

    with open('/Volumes/Data/zeme.txt', 'r') as f:
        reader = csv.reader(f, delimiter='|')
        for row in reader:
            iso = row[0]
            valid_from = row[1]
            valid_until = row[2]
            code2 = row[3]
            code3 = row[4]
            name_cs = row[5]
            name_cs_short = row[6].lower()
            name_en = row[7]
            name_en_short = row[8].lower()
            code2eu = row[9]
            eu_since = row[10]
            eu_until = row[11]

            if valid_until == None:
                break

            eu_member = (eu_since is not None) and (eu_until is None)
            if eu_member:
                g.add(zeme_eu['members'], skos.member, zeme_eu[code2eu])

            for t in [
                (zeme_iso[iso], RDF.type, skos.Concept),
                (zeme_iso[iso], skos.prefLabel, Literal(name_cs, lang="cs")),
                (zeme_iso[iso], skos.altLabel, Literal(name_cs_short, lang="cs")),
                (zeme_iso[iso], skos.prefLabel, Literal(name_en, lang="en")),
                (zeme_iso[iso], skos.altLabel, Literal(name_en_short, lang="en")),
                (zeme_iso[iso], skos.notation, Literal(iso)),
                (zeme_iso[iso], skos.inScheme, rdflib.URIRef(zeme_iso_ns)),

                (zeme[code3], RDF.type, skos.Concept),
                (zeme[code3], skos.prefLabel, Literal(name_cs, lang="cs")),
                (zeme[code3], skos.altLabel, Literal(name_cs_short, lang="cs")),
                (zeme[code3], skos.prefLabel, Literal(name_en, lang="en")),
                (zeme[code3], skos.altLabel, Literal(name_en_short, lang="en")),
                (zeme[code3], skos.notation, Literal(code3)),
                (zeme[code3], skos.notation, Literal(code2)),
                (zeme[code3], skos.inScheme, rdflib.URIRef(zeme_ns)),

                (zeme_eu[code2eu], RDF.type, skos.Concept),
                (zeme_eu[code2eu], skos.prefLabel, Literal(name_cs, lang="cs")),
                (zeme_eu[code2eu], skos.altLabel, Literal(name_cs_short, lang="cs")),
                (zeme_eu[code2eu], skos.prefLabel, Literal(name_en, lang="en")),
                (zeme_eu[code2eu], skos.altLabel, Literal(name_en_short, lang="en")),
                (zeme_eu[code2eu], skos.notation, Literal(code2eu)),
                (zeme_eu[code2eu], skos.inScheme, rdflib.URIRef(zeme_eu_ns)),

                (zeme_iso[iso], skos.exactMatch, zeme[code3]),
                (zeme[code3], skos.exactMatch, zeme_iso[iso]),
                (zeme_eu[code2eu], skos.exactMatch, zeme_iso[iso]),
            ]:
                g.add(t)
    g.serialize(destination=zeme_out, format="turtle")


def loadIco(ico):
    #url_base = "https://wwwinfo.mfcr.cz/cgi-bin/ares/darv_vreo.cgi?ico="

    #r = requests.get(url_base + ico)
    #r.raise_for_status()

    base_dir = "/Volumes/Data/VYSTUP/DATA/"
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


def parseAdresa(record):
    def clean(text):
        return " ".join(text.strip().split())
    sidlo_ruian_ = record.find('are:ruianKod')
    if None != sidlo_ruian_:
        sidlo_ruian = sidlo_ruian_.text
    else:
        sidlo_ruian = None
    stat_ = record.find('are:stat')
    if stat_ != None:
        stat = clean(stat_.text)
    else:
        stat = None

    psc_=record.find('are:psc')
    if psc_ != None:
        psc = clean(psc_.text)
    else:
        psc = None
    okres_ = record.find('are:okres')
    if None != okres_:
        okres = clean(okres_.text)
    else:
        okres = None
    obec_ = record.find('are:obec')
    if obec_ != None:
        obec = clean(obec_.text)
    else:
        obec = None

    castObce_ = record.find('are:castObce')
    if castObce_ != None:
        castObce = clean(castObce_.text)
    else:
        castObce = None
    mop_ = record.find('are:mop')
    if None != mop_:
        mop = clean(mop_.text)
    else:
        mop = None
    ulice_ = record.find('are:ulice')
    if None != ulice_:
        ulice = clean(ulice_.text)
    else:
        ulice = ""
    cisloPop_ = record.find('are:cisloPop')
    if None != cisloPop_:
        cisloPop = clean(cisloPop_.text)
    else:
        cisloPop = ""
    cisloOr_ = record.find('are:cisloOr')
    if None != cisloOr_:
        cisloOr = clean(cisloOr_.text)
    else:
        cisloOr = None
    sidlo = Sidlo(stat, psc, okres, obec, castObce, mop, ulice, cisloPop, cisloOr)
    sidlo.ruian = sidlo_ruian
    return sidlo


def parseVypis(vypis):
    def clean(text):
        return " ".join(text.strip().split())

    if vypis is None:
        return None

    udaje = vypis.find('are:Zakladni_udaje')
    try:
        ico = udaje.find('are:ICO').text
    except:
        print("Chybi ICO")
        print(udaje)
        return None

    _x = udaje.find('are:Rejstrik')
    if _x is not None:
        rejstrik = Rejstrik[_x.text]
    else:
        rejstrik = None

    _x = udaje.find('are:ObchodniFirma')
    if _x is not None:
        firma = _x.text
    else:
        firma = None

    sidlo_ruian_ = udaje.find('are:ruianKod')
    if None != sidlo_ruian_:
        sidlo_ruian = sidlo_ruian_.text
    else:
        sidlo_ruian = None
    zapis = udaje.find('are:DatumZapisu').text

    sidlo = udaje.find('are:Sidlo')
    if sidlo is not None:
        stat_ = sidlo.find('are:stat')
        if stat_ != None:
            stat = clean(stat_.text)
        else:
            stat = None

        psc_ = sidlo.find('are:psc')
        if psc_ != None:
            psc = clean(psc_.text)
        else:
            psc = None
        okres_ = sidlo.find('are:okres')
        if None != okres_:
            okres = clean(okres_.text)
        else:
            okres = None
        obec_ = sidlo.find('are:obec')
        if obec_ != None:
            obec = clean(obec_.text)
        else:
            obec = None

        castObce_ = sidlo.find('are:castObce')
        if castObce_ != None:
            castObce = clean(castObce_.text)
        else:
            castObce = None
        mop_ = sidlo.find('are:mop')
        if None != mop_:
            mop = clean(mop_.text)
        else:
            mop = None
        ulice_ = sidlo.find('are:ulice')
        if None != ulice_:
            ulice = clean(ulice_.text)
        else:
            ulice = ""
        cisloPop_ = sidlo.find('are:cisloPop')
        if None != cisloPop_:
            cisloPop = clean(cisloPop_.text)
        else:
            cisloPop = ""
        cisloOr_ = sidlo.find('are:cisloOr')
        if None != cisloOr_:
            cisloOr = clean(cisloOr_.text)
        else:
            cisloOr = None
        sidlo = Sidlo(stat, psc, okres, obec, castObce, mop, ulice, cisloPop, cisloOr)
        sidlo.ruian = sidlo_ruian
    else:
        sidlo = None
    cinnost = []
    cinnosti = udaje.find('are:Cinnosti')
    if None != cinnosti:
        predmet = cinnosti.find('are:PredmetPodnikani')
        if None != predmet:
            cinnost = [" ".join(predmet.text.lower().strip().split()) for predmet in predmet.find_all('are:Text')]

    c = Company(ico, rejstrik, firma, sidlo, zapis, cinnost)
    c.members = []
    for cl in vypis.find_all('are:Clen'):
        dza = cl['dza']
        if 'dvy' in cl.attrs:
            dvy = cl['dvy']
        else:
            dvy = None
        for fo in cl.find_all('are:fosoba'):
            try:
                try:
                    adr = parseAdresa(fo.find('are:adresa'))
                except:
                   adr = None
                try:
                   jm = fo.find('are:jmeno').text
                except:
                   jm = ""
                try:
                   pr = fo.find('are:prijmeni').text
                except:
                   pr = ""
                try:
                    fce = fo.parent.find('are:funkce').find('are:nazev').text
                except:
                    fce = None
                if fo.parent.name == "Zastoupeni":
                    print(cl)
                else:
                    organ = fo.parent.parent.find('are:Nazev').text
                    statutar = fo.parent.parent.name == "are:Statutarni_organ"
                    c.members.append(MemberFO(jm, pr, fce, organ, adr, statutar, dza, dvy))
            except:
                print(fo.parent.name)
                print(fo.parent)
                raise
        for po in cl.find_all('are:posoba'):
            try:
                try:
                    adr = parseAdresa(po.find('are:adresa'))
                except:
                    adr = None
                of = po.find('are:ObchodniFirma').text
                try:
                    fce = po.parent.find('are:funkce').find('are:nazev').text
                except:
                    fce = None
                organ = po.parent.parent.find('are:Nazev').text
                statutar = po.parent.parent.name == "are:Statutarni_organ"
                try:
                    ico = po.find('are:ICO').text
                except:
                    ico = None
                c.members.append(MemberPO(of, fce, organ, adr, statutar, dza, dvy, ico))
            except:
                print(cl.parent)
                raise
    return c


map = dict()
def getUUIDforActivity(a):
    #TODO: kebap-case
    global map
    if a in map.keys():
        x = map[a]
    else:
        x = uuid.uuid4()
        map[a] = x
    return x


typy = set()
typ_map = {
 's.r.o.' : Forma.SRO,
 'spol. s r.o.': Forma.SRO,
 'v.o.s.': Forma.VOS,
 'z.s.': Forma.ZS,
 'zapsaný spolek': Forma.ZS,
 'z. s.': Forma.ZS,
 'o.s.': Forma.ZS,
 'o. s.': Forma.ZS,
 'SE': Forma.SE,
 'S.E.': Forma.SE,
 'S. E.': Forma.SE,
 'a.s.': Forma.AS,
 'a. s.': Forma.AS
}


def triplifyCompany(company):
    global typy
    global typ_map

    g = rdflib.Graph()

    if company is None:
        return g

    gr = rdflib.Namespace('http://purl.org/goodrelations/v1#')
    schema = rdflib.Namespace('http://schema.org/')
    base_ns = 'http://data.eghuro.cz/resource/'
    rejstrik_ns = base_ns + 'public-register/'
    rejstrik = rdflib.Namespace(rejstrik_ns)
    org = rdflib.Namespace('http://www.w3.org/ns/org#')
    foaf = rdflib.Namespace('http://xmlns.com/foaf/0.1/')
    skos = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')
    dc = rdflib.Namespace('http://purl.org/dc/elements/1.1/')
    time = rdflib.Namespace('http://www.w3.org/2006/time#')

    g.bind('gr', gr)
    g.bind('schema', schema)
    g.bind('org', org)
    g.bind('foaf', foaf)
    g.bind('skos', skos)
    g.bind('dc', dc)
    g.bind('time', time)

    base_ns = 'http://data.eghuro.cz/resource/'

    ico_ns = base_ns + 'business-entity/'
    business = rdflib.URIRef(ico_ns + 'CZ' + company.ico)

    zeme_iso_ns = base_ns + 'country/iso/'
    zeme_iso = rdflib.Namespace(zeme_iso_ns)

    activity_ns = base_ns + 'business-activity/'
    activity = rdflib.Namespace(activity_ns)

    person_ns = base_ns + 'person/'
    person = rdflib.Namespace(person_ns)

    b1 = rdflib.BNode()
    #TODO: b1 = rdflib.URIRef(ico_ns + 'CZ' + company.ico+"/address")

    btype = schema.Organization
    if company.rejstrik == Rejstrik.OR:
        btype = schema.Corporation

    if company.sidlo != None:
        if company.sidlo.cisloOr != None:
            addr_str = company.sidlo.ulice + " " + company.sidlo.cisloPop + "/" + company.sidlo.cisloOr
        elif company.sidlo.cisloPop != None:
            addr_str = company.sidlo.ulice + " " + company.sidlo.cisloPop
        else:
            addr_str = company.sidlo.ulice
        addr_str = addr_str.strip()

        if company.sidlo.psc == None:
            company.sidlo.psc = ""

        if company.sidlo.okres == None:
            company.sidlo.okres = ""

        # TODO (not used when generating last data)
        #if company.sidlo.obec == None:
        #    company.sidlo.obec == ""

    if company.firma != None:
        if "v likvidaci" in company.firma:
            company.firma = company.firma.strip("v likvidaci")[0]
            company.likvidace = True
        else:
            company.likvidace = False

        if company.firma.replace(" ", "").replace(".","").endswith("sro"):
            typ = "s.r.o."
        else:
            x = company.firma.split(',')
            if len(x) > 1:
                typ = x[-1]
                typy.add(typ)
            else:
                typ = None
    else:
        typ = None

    for t in [
        (business, RDF.type, gr.BusinessEntity),
        (business, RDF.type, btype),
        (business, RDF.type, foaf.Organization),
        (business, RDF.type, org.FormalOrganization),
        (business, schema.identifier, rdflib.Literal(company.ico)),
        (business, org.identifier, rdflib.Literal(company.ico)),
    ]:
        g.add(t)

    if company.firma != None:
        for t in [
            (business, gr.legalName, rdflib.Literal(company.firma, lang="cs")),
            (business, schema.legalName, rdflib.Literal(company.firma, lang="cs")),
            (business, skos.prefLabel, rdflib.Literal(company.firma, lang="cs")),
        ]:
            g.add(t)
        if company.likvidace:
            g.add((business, foaf.status, rdflib.URIRef(base_ns + "business-in-liquidation")))

    if company.sidlo != None:
        for t in [
            (business, schema.address, b1),
            (business, org.hasRegisteredSite, b1),
            (b1, RDF.type, schema.PostalAddress),
            (b1, RDF.type, org.Site),
            (b1, org.siteOf, business),
            (b1, schema.postalCode, rdflib.Literal(company.sidlo.psc)),
            (b1, schema.addressLocality, rdflib.Literal(company.sidlo.obec, lang="cs")),
            (b1, schema.streetAddress, rdflib.Literal(addr_str, lang="cs")),
            (b1, schema.addressCountry, zeme_iso[company.sidlo.stat]),
            (b1, schema.identifier, rdflib.Literal(company.sidlo.ruian))
        ]:
            g.add(t)
        if len(company.sidlo.okres) > 0:
            g.add((b1, schema.region, rdflib.Literal(company.sidlo.okres, lang="cs")))

    if company.rejstrik is not None:
        g.add((business, dc.isReferencedBy, rejstrik[company.rejstrik.name]))


    if company.firma is not None:
        if typ is None:
            typ = company.firma.split()[-1]
        typ = typ.strip()
        if typ in typ_map.keys():
            ot = rdflib.Namespace(base_ns + 'organisation-type/')
            g.add( (business, dc.type, ot[typ_map[typ].name]) )
        else:
            print(company.firma + ": \"" + typ + "\"")

    g.add((rdflib.URIRef(activity_ns), RDF.type, skos.ConceptScheme))
    for activ in company.cinnosti:
        aid = str(getUUIDforActivity(activ))
        for t in [
            (activity[aid], RDF.type, skos.Concept),
            (activity[aid], skos.prefLabel, Literal(activ, lang="cs")),
            (activity[aid], skos.inScheme, rdflib.URIRef(activity_ns)),
            (business, org.classification, activity[aid])
        ]:
            g.add(t)

    for member in company.members:
        #ba = rdflib.BNode()
        if type(member) is MemberFO:
            mid = str(getUUIDforActivity(" ".join([member.jmeno, member.prijmeni]).strip()))
            for t in [
                (person[mid], RDF.type, foaf.Person),
                (person[mid], foaf.givenName, Literal(member.jmeno)),
                (person[mid], foaf.familyName, Literal(member.prijmeni)),
            ]:
                g.add(t)
            x = mid
        else:
            oid = str(getUUIDforActivity(member.nazev))
            for t in [
                (person[oid], RDF.type, foaf.Organization),
                (person[oid], skos.prefLabel, Literal(member.nazev))
            ]:
                g.add(t)
            if member.ico != None:
                g.add((person[oid], org.identifier, Literal(member.ico)))
            x = oid
        #adresa
        if member.adresa != None:
            if member.adresa.cisloOr != None:
                addr_str = member.adresa.ulice + " " + member.adresa.cisloPop + "/" + member.adresa.cisloOr
            elif member.adresa.cisloPop != None:
                addr_str = member.adresa.ulice + " " + member.adresa.cisloPop
            else:
                addr_str = member.adresa.ulice
            addr_str = addr_str.strip()

            if member.adresa.psc == None:
                member.adresa.psc = ""

            if member.adresa.okres == None:
                member.adresa.okres = ""

            bb = rdflib.BNode()
            #TODO: bb = rdflib.URIRef(person_ns + x + "/address")
            for t in [
                (person[x], schema.address, bb),
                (bb, RDF.type, schema.PostalAddress),
                (bb, schema.postalCode, rdflib.Literal(member.adresa.psc)),
                (bb, schema.addressLocality, rdflib.Literal(member.adresa.obec)),
                (bb, schema.streetAddress, rdflib.Literal(addr_str)),
                (bb, schema.addressCountry, zeme_iso[member.adresa.stat]),
            ]:
                g.add(t)

        mem = person[x]
        oid = str(getUUIDforActivity(member.organ))
        organ = rdflib.URIRef(str(business) + "/organ/" + oid)

        for t in [
            (organ, RDF.type, org.Organization),
            (organ, org.subOrganizationOf, business),
            (organ, skos.prefLabel, rdflib.Literal(member.organ))
        ]:
            g.add(t)

        inte = rdflib.BNode()
        mid = str(uuid.uuid4())
        membership = rdflib.URIRef(organ + "/membership/" + mid)
        #TODO: inte = rdflib.URIRef(organ + "/membership/" + mid + "/interval")
        for t in [
            (inte, RDF.type, time.ProperInterval),
            (inte, time.intervalStarts, rdflib.Literal(member.zapsan, datatype=XSD.date)),
            (inte, time.intervalFinishes, rdflib.Literal(member.vyskrtnut, datatype=XSD.date)), #FIXME
            (membership, RDF.type, org.Membership),
            (membership, org.member, mem),
            (membership, org.organization, organ),
            (membership, org.memberDuring, inte),
        ]:
            g.add(t)
        if member.funkce is not None:
            rid = str(getUUIDforActivity(member.funkce.lower()))
            role = rdflib.URIRef(str(business) + "/role/" + rid)
            role_g = rdflib.URIRef(base_ns + "business-role/" + rid)
            for t in [
                (role, RDF.type, org.Role),
                (role, skos.prefLabel, rdflib.Literal(member.funkce.lower())),
                (role_g, RDF.type, org.Role),
                (role_g, skos.prefLabel, rdflib.Literal(member.funkce.lower())),
                (membership, org.role, role),
                (membership, org.role, role_g),
             ]:
                 g.add(t)
        #statutarni organ?

    return g

if __name__ == '__main__':
    try:
        prepare("rejstrik.ttl", "zeme.ttl")
        g = rdflib.ConjunctiveGraph()
        for _,_,files in os.walk('/Volumes/Data/VYSTUP/DATA/'):
            for ico in files:
                ico = ico.split('.')[0]
                print(ico)
                g.parse(data=triplifyCompany(parseVypis(loadIco(ico))).serialize(format='turtle'), format='turtle')
        g.serialize(destination='ares.ttl', format='turtle')

        for typ in typy:
            print(typ)
    except:
        print("\a\a")
        raise
    #print(triplifyCompany(parseVypis(loadIco('27074358'))).serialize(format='turtle'))
