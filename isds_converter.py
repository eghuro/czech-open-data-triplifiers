import requests
import rdflib
from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from bs4 import BeautifulSoup
import datetime
import os


box_class = URIRef('http://data.eghuro.cz/resource/databox-model/databox')
type_class = URIRef('http://data.eghuro.cz/resource/databox-model/type')
box_type_ns = 'http://data.eghuro.cz/resource/databox-model/type'
box_type = rdflib.Namespace(box_type_ns + '/')
box_type_scheme = URIRef(box_type_ns)
box_subtype = 'http://data.eghuro.cz/resource/databox-model/subtype'
box_subtype_scheme = URIRef(box_subtype)
pdz_property = URIRef('http://data.eghuro.cz/resource/databox-model/pdz')
ovm_property = URIRef('http://data.eghuro.cz/resource/databox-model/ovm')
master_property = URIRef('http://data.eghuro.cz/resource/databox-model/master')
ovm_id_property = URIRef('http://data.eghuro.cz/resource/databox-model/ovm/id')


def create_header(g):
    skos = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')
    g.bind('skos', skos)

    for t in [
        (box_class, RDF.type, RDFS.Class),
        (type_class, RDF.type, RDF.Property),
        (type_class, RDFS.domain, box_class),
        (type_class, RDFS.range, box_type_scheme),
        (pdz_property, RDF.type, RDF.Property),
        (ovm_property, RDF.type, RDF.Property),
        (pdz_property, RDFS.domain, box_class),
        (ovm_property, RDFS.domain, box_class),
        (master_property, RDF.type, RDF.Property),
        (master_property, RDFS.domain, box_class),
        (master_property, RDFS.domain, box_class),
        (ovm_id_property, RDF.type, RDF.Property),
        (ovm_id_property, RDFS.domain, box_class),

        (box_type_scheme, RDF.type, skos.ConceptScheme),
        (box_type.OVM, RDF.type, skos.Concept),
        (box_type.OVM, skos.inScheme, box_type_scheme),
        (box_type.OVM, skos.notation, Literal("OVM")),
        (box_type.OVM, RDFS.label, Literal("OVM")),
        (box_type.OVM, RDFS.comment, Literal("DS běžného OVM vzniklá ze zákona – vzniká a edituje se pouze z externího podnětu z evidence Seznam OVM  - §6  odst. 1 resp. z Rejstříku OVM.")),
        (box_type.PO, RDF.type, skos.Concept),
        (box_type.PO, skos.inScheme, box_type_scheme),
        (box_type.PO, skos.notation, Literal("PO")),
        (box_type.PO, RDFS.label, Literal("PO")),
        (box_type.PO, RDFS.comment, Literal("DS právnické osoby zřízené zákonem ale ne v OR (hlášená z ROS) - §5 odst. 1.")),
        (box_type.PFO, RDF.type, skos.Concept),
        (box_type.PFO, skos.inScheme, box_type_scheme),
        (box_type.PFO, skos.notation, Literal("PFO")),
        (box_type.PFO, RDFS.label, Literal("PFO")),
        (box_type.PFO, RDFS.comment, Literal("DS podnikající fyzické osoby vzniklá na žádost - §4 odst. 1.")),
        (box_type.FO, RDF.type, skos.Concept),
        (box_type.FO, skos.inScheme, box_type_scheme),
        (box_type.FO, skos.notation, Literal("FO")),
        (box_type.FO, RDFS.label, Literal("FO")),
        (box_type.FO, RDFS.comment, Literal("DS fyzické osoby, vzniklá na žádost - §3 odst. 1")),

        (box_type["OVM-PO"], RDF.type, skos.Concept),
        (box_type["OVM-PO"], skos.inScheme, box_subtype_scheme),
        (box_type["OVM-PO"], skos.notation, Literal("OVM_PO")),
        (box_type["OVM-PO"], RDFS.label, Literal("OVM_PO")),
        (box_type["OVM-PO"], RDFS.comment, Literal("Vzniká změnou typu poté, co byl subjekt odpovídající existující schránce typu PO nebo PO_REQ zapsán do Rejstříku OVM. PO případném výmazu z Rejstříku OVM se opět typ změní na původní PO nebo PO_REQ (odpovídá tzv. „povyšování schránek“ před novelou zákona o ISDS).")),
        (box_type["OVM-PO"], skos.narrower, box_type.PO),
        (box_type["OVM-PO"], skos.narrower, box_type.OVM),
        (box_type.OVM, skos.broader, box_type["OVM-PO"]),
        (box_type.PO, skos.broader, box_type["OVM-PO"]),

        (box_type["OVM-PFO"], RDF.type, skos.Concept),
        (box_type["OVM-PFO"], skos.inScheme, box_subtype_scheme),
        (box_type["OVM-PFO"], skos.notation, Literal("OVM_PFO")),
        (box_type["OVM-PFO"], RDFS.label, Literal("OVM_PFO")),
        (box_type["OVM-PFO"], RDFS.comment, Literal("Vzniká poté, co subjekt PFO byl zapsán do Rejstříku OVM")),
        (box_type["OVM-PFO"], skos.narrower, box_type.PFO),
        (box_type["OVM-PFO"], skos.narrower, box_type.OVM),
        (box_type.OVM, skos.broader, box_type["OVM-PFO"]),
        (box_type.PFO, skos.broader, box_type["OVM-PFO"]),

        (box_type["OVM-FO"], RDF.type, skos.Concept),
        (box_type["OVM-FO"], skos.inScheme, box_subtype_scheme),
        (box_type["OVM-FO"], skos.notation, Literal("OVM_FO")),
        (box_type["OVM-FO"], RDFS.label, Literal("OVM_FO")),
        (box_type["OVM-FO"], RDFS.comment, Literal("Vzniká poté, co je fyzická osoba (tj. bez IČO) zapsána do Rejstříku OVM.")),
        (box_type["OVM-FO"], skos.narrower, box_type.FO),
        (box_type["OVM-FO"], skos.narrower, box_type.OVM),
        (box_type.OVM, skos.broader, box_type["OVM-FO"]),
        (box_type.FO, skos.broader, box_type["OVM-FO"]),

        (box_type["OVM-REQ"], RDF.type, skos.Concept),
        (box_type["OVM-REQ"], skos.inScheme, box_subtype_scheme),
        (box_type["OVM-REQ"], skos.notation, Literal("OVM_REQ")),
        (box_type["OVM-REQ"], RDFS.label, Literal("OVM_REQ")),
        (box_type["OVM-REQ"], RDFS.comment, Literal("Další DS jiné OVM, vzniklá na žádost (§6 a 7) – vzniká pouze z externího podnětu z evidence Seznam OVM.")),
        (box_type["OVM-REQ"], skos.narrower, box_type.OVM),
        (box_type.OVM, skos.broader, box_type["OVM-FO"]),

        (box_type["PFO-auditor"], RDF.type, skos.Concept),
        (box_type["PFO-auditor"], skos.inScheme, box_subtype_scheme),
        (box_type["PFO-auditor"], skos.notation, Literal("PFO_AUDITOR")),
        (box_type["PFO-auditor"], RDFS.label, Literal("PFO_AUDITOR")),
        (box_type["PFO-auditor"], RDFS.comment, Literal("DS konkrétního auditora.")),
        (box_type["PFO-auditor"], skos.narrower, box_type.PFO),
        (box_type.PFO, skos.broader, box_type["PFO-auditor"]),

        (box_type["PFO-advok"], RDF.type, skos.Concept),
        (box_type["PFO-advok"], skos.inScheme, box_subtype_scheme),
        (box_type["PFO-advok"], skos.notation, Literal("PPFO_ADVOK")),
        (box_type["PFO-advok"], RDFS.label, Literal("PFO_ADVOK")),
        (box_type["PFO-advok"], RDFS.comment, Literal("DS konkrétního advokáta, ne společnosti (hlášená z ROS).")),
        (box_type["PFO-advok"], skos.narrower, box_type.PFO),
        (box_type.PFO, skos.broader, box_type["PFO-advok"]),

        (box_type["PFO-danpor"], RDF.type, skos.Concept),
        (box_type["PFO-danpor"], skos.inScheme, box_subtype_scheme),
        (box_type["PFO-danpor"], skos.notation, Literal("PFO_DANPOR")),
        (box_type["PFO-danpor"], RDFS.label, Literal("PFO_DANPOR")),
        (box_type["PFO-danpor"], RDFS.comment, Literal("DS konkrétního daňového poradce (hlášená z ROS).")),
        (box_type["PFO-danpor"], skos.narrower, box_type.PFO),
        (box_type.PFO, skos.broader, box_type["PFO-danpor"]),

        (box_type["PFO-insspr"], RDF.type, skos.Concept),
        (box_type["PFO-insspr"], skos.inScheme, box_subtype_scheme),
        (box_type["PFO-insspr"], skos.notation, Literal("PFO_INSSPR")),
        (box_type["PFO-insspr"], RDFS.label, Literal("PFO_INSSPR")),
        (box_type["PFO-insspr"], RDFS.comment, Literal("DS insolvenčního správce (hlášená z ROS).")),
        (box_type["PFO-insspr"], skos.narrower, box_type.PFO),
        (box_type.PFO, skos.broader, box_type["PFO-insspr"]),

        (box_type["PO-req"], RDF.type, skos.Concept),
        (box_type["PO-req"], skos.inScheme, box_subtype_scheme),
        (box_type["PO-req"], skos.notation, Literal("PO_REQ")),
        (box_type["PO-req"], RDFS.label, Literal("PO_REQ")),
        (box_type["PO-req"], RDFS.comment, Literal("DS právnické osoby vzniklá na žádost - §5 odst. 2.")),
        (box_type["PO-req"], skos.narrower, box_type.PO),
        (box_type.PO, skos.broader, box_type["PO-req"])
    ]:
        g.add(t)

def triplify_box(box_xml, g):
    schema = rdflib.Namespace('http://schema.org/')
    foaf = rdflib.Namespace('http://xmlns.com/foaf/0.1/')
    g.bind('schema', schema)
    g.bind('foaf', foaf)

    box_ns = 'http://data.eghuro.cz/resource/databox/'
    box = rdflib.Namespace(box_ns)

    box_id = box_xml.find('id').text
    #print(box_id)
    boxtype = box_xml.find('type').text
    boxsubtype = box_xml.find('subtype').text
    pdz = box_xml.find('pdz').text
    ovm = box_xml.find('ovm').text

    for t in [
        (box[box_id], RDF.type, box_class),
        (box[box_id], type_class, box_type[boxtype]),
        (box[box_id], pdz_property, Literal(pdz, datatype=XSD.boolean)),
        (box[box_id], ovm_property, Literal(ovm, datatype=XSD.boolean)),
        (box[box_id], schema.identifier, Literal(box_id)),
    ]:
        g.add(t)

    masterId = box_xml.find('masterId')
    if None != masterId:
        g.add((box[box_id], master_property, box[masterId.text]))

    owner = rdflib.Namespace(str(box[box_id])).owner

    name = box_xml.find('name')
    if len(name.person.lastName.text) > 0:
        for t in [
            (owner, RDF.type, foaf.Person),
            (owner, foaf.familyName, Literal(name.person.lastName.text)),
            (owner, foaf.firstName, Literal(name.person.firstName.text)),
            (owner, foaf.account, box[box_id])
        ]:
            g.add(t)

    if len(name.tradeName.text) > 0:
        for t in [
            (owner, RDF.type, schema.Organization),
            (owner, RDF.type, foaf.Organization),
            (owner, schema.legalName, Literal(name.tradeName.text)),
            (owner, foaf.account, box[box_id])
        ]:
            g.add(t)

    box_ico = box_xml.find('ico')
    if len(box_ico.text) > 0:
        g.add((owner, schema.identifier, Literal(box_ico.text)))

    box_idOvm = box_xml.find('idOVM')
    if len(box_idOvm.text) > 0:
        g.add((box[box_id], ovm_id_property, Literal(box_idOvm.text)))

    address = rdflib.Namespace(str(owner)).address
    box_adr = box_xml.find('address')
    city = box_adr.city.text
    district = box_adr.district.text
    street = box_adr.street.text
    cp = box_adr.cp.text
    co = box_adr.co.text
    ce = box_adr.ce.text
    zip = box_adr.zip.text
    if box_adr.addressPoint is not None:
        addressPoint = box_adr.addressPoint.text
    else:
        addressPoint = ""
    state = box_adr.state.text
    fullAddress = box_adr.fullAddress.text
    streetAddress = street + "/".join([cp, co, ce])

    for t in [
        (address, RDF.type, schema.PostalAddress),
        (address, schema.addressCountry, Literal(state)),
        (address, schema.identifier, Literal(addressPoint)),
        (address, schema.addressLocality, Literal(city)),
        (address, schema.postalCode, Literal(zip)),
        (address, schema.streetAddress, Literal(streetAddress)),
        (owner, schema.address, address),
        (owner, schema.address, Literal(fullAddress))
    ]:
        g.add(t)
    return str(box[box_id])

dcat = rdflib.Namespace('http://www.w3.org/ns/dcat#')
dcterms = rdflib.Namespace('http://purl.org/dc/terms/')
foaf = rdflib.Namespace('http://xmlns.com/foaf/0.1/')
vcard = rdflib.Namespace('http://www.w3.org/2006/vcard/ns#')

ds = URIRef('https://data.eghuro.cz/resource/dataset/databox')
distr_ns = rdflib.Namespace('https://data.eghuro.cz/resource/distribution/databox/')

title_cs = 'Seznam držitelů datových schránek'
def create_dcat(ttl_size, today):
    g = rdflib.ConjunctiveGraph()
    g.bind('dcat', dcat)
    g.bind('dcterms', dcterms)
    for t in [
        (ds, RDF.type, dcat.Dataset),
        (ds, dcterms.accrualPeriodicity, URIRef('http://publications.europa.eu/resource/authority/frequency/DAILY')),
        (ds, dcterms.description, Literal(title_cs, lang='cs')),
        (ds, dcterms.issued, Literal('2018-12-31', datatype=XSD.date)),
        (ds, dcterms.modified, Literal(today, datatype=XSD.dateTime)),
        (ds, dcterms.language, URIRef('http://publications.europa.eu/resource/authority/language/CES')),
        (ds, dcterms.publisher, URIRef('https://eghuro.cz/#me')),
        (ds, dcterms.contactPoint, URIRef('https://eghuro.cz/#me')),
        (ds, dcterms.rightsHolder, URIRef('https://www.mvcr.cz')),
        (ds, dcterms.source, URIRef('https://www.mojedatovaschranka.cz/sds/welcome.do?part=opendata')),
        (ds, dcterms.spatial, URIRef('http://publications.europa.eu/resource/authority/country/CZE')),
        (ds, dcterms.title, Literal(title_cs, lang='cs')),
        (ds, RDFS.comment, Literal(title_cs, lang='cs')),

        (ds, dcat.distribution, distr_ns['a']),
        (ds, dcat.distribution, distr_ns['b']),

        (distr_ns['0'], RDF.type, dcat.Distribution),
        (distr_ns['0'], dcterms.title, Literal('SPARQL Endpoint')),
        (distr_ns['0'], dcat['accessURL'], URIRef('https://data.eghuro.cz/sparql')),

        (distr_ns['1'], RDF.type, dcat.Distribution),
        (distr_ns['1'], dcat['accessURL'], URIRef('https://data.eghuro.cz/dump/databox/databox.ttl')),
        (distr_ns['1'], dcterms.title, Literal(title_cs)),
        (distr_ns['1'], dcterms['format'], URIRef('http://publications.europa.eu/resource/authority/file-type/RDF_TURTLE')),
        (distr_ns['1'], dcat['mediaType'], Literal('text/turtle')),
        (distr_ns['1'], dcat['byteSize'], Literal(ttl_size, datatype=XSD.decimal))
    ]:
        g.add(t)
    g.serialize(destination='dcat.ttl', format='turtle')


def create_void(example, today):
    void = rdflib.Namespace('http://rdfs.org/ns/void#')
    g = rdflib.ConjunctiveGraph()
    g.bind('void', void)
    g.bind('dcterms', dcterms)
    g.bind('foaf', foaf)
    for t in [
        (ds, RDF.type, void.Dataset),
        (ds, void.sparqlEndpoint, URIRef('https://data.eghuro.cz/sparql')),
        (ds, void.exampleResource, URIRef(example)),
        (ds, void.uriSpace, URIRef('http://data.eghuro.cz/resource/databox')),
        (ds, void.vocabulary, URIRef('http://schema.org/')),
        (ds, void.vocabulary, URIRef('http://xmlns.com/foaf/0.1/')),
        (ds, foaf.homepage, URIRef('https://www.mojedatovaschranka.cz')),
        (ds, dcterms.accrualPeriodicity, URIRef('http://publications.europa.eu/resource/authority/frequency/DAILY')),
        (ds, dcterms.description, Literal(title_cs, lang='cs')),
        (ds, dcterms.issued, Literal('2018-12-31', datatype=XSD.date)),
        (ds, dcterms.modified, Literal(today, datatype=XSD.dateTime)),
        (ds, dcterms.language, URIRef('http://publications.europa.eu/resource/authority/language/CES')),
        (ds, dcterms.publisher, URIRef('https://eghuro.cz/#me')),
        (ds, dcterms.contactPoint, URIRef('https://eghuro.cz/#me')),
        (ds, dcterms.rightsHolder, URIRef('https://www.mvcr.cz')),
        (ds, dcterms.source, URIRef('https://www.mojedatovaschranka.cz/sds/welcome.do?part=opendata')),
        (ds, dcterms.spatial, URIRef('http://publications.europa.eu/resource/authority/country/CZE')),
        (ds, dcterms.title, Literal(title_cs, lang='cs')),
        (ds, void.feature, URIRef('http://www.w3.org/ns/formats/Turtle')),
        (ds, void.dataDump, URIRef('https://data.eghuro.cz/dump/databox/databox.ttl'))
    ]:
        g.add(t)
    g.serialize(destination='void.ttl', format='turtle')


def triplify_current():
    g = rdflib.ConjunctiveGraph()

    create_header(g)

    for url in [
        "https://www.mojedatovaschranka.cz/sds/datafile.do?format=xml&service=seznam_ds_po",
        "https://www.mojedatovaschranka.cz/sds/datafile.do?format=xml&service=seznam_ds_pfo",
        "https://www.mojedatovaschranka.cz/sds/datafile.do?format=xml&service=seznam_ds_fo",
        "https://www.mojedatovaschranka.cz/sds/datafile.do?format=xml&service=seznam_ds_ovm"
    ]:
        print(url)
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'lxml-xml')
        b = None
        for box in soup.find_all('box'):
            b = triplify_box(box, g)

    g.serialize(destination='isds.ttl', format='turtle')
    return b

if __name__ == '__main__':
    example = triplify_current()
    size = os.stat('isds.ttl').st_size
    today = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ%z')

    create_dcat(size, today)
    create_void(example, today)
