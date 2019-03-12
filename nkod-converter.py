import rdflib
from rdflib.namespace import RDF

def transform(p, nkod_ds, my_ds_ns):
    if p.startswith(nkod_ds):
        #for a, b in [
            #("záznam", "record"),
            #("kontaktní-bod", "contact-point"),
            #("časové-pokrytí", "temporal")]:
            #if p.endswith(a):
            #    p = p[:-len(a)] + b
            #    break

        p = my_ds_ns[p[len(nkod_ds):]]
    elif type(p) == rdflib.Literal:
        p = rdflib.Literal(p)
    else:
        p = rdflib.URIRef(p)
    return p


def convert():
    g = rdflib.ConjunctiveGraph()

    dcat = rdflib.Namespace('http://www.w3.org/ns/dcat#')
    dcterms = rdflib.Namespace('http://purl.org/dc/terms/')
    foaf = rdflib.Namespace('http://xmlns.com/foaf/0.1/')
    void = rdflib.Namespace('http://rdfs.org/ns/void#')
    vcard = rdflib.Namespace('http://www.w3.org/2006/vcard/ns#')
    schema = rdflib.Namespace('http://schema.org/')

    nkod_ds = 'https://data.gov.cz/zdroj/datová-sada/'
    my_ds = 'https://data.eghuro.cz/resource/dataset/'
    my_ds_ns = rdflib.Namespace(my_ds)

    nkod_voc = 'https://data.gov.cz/slovník/nkod/'
    nkod_voc_ns = rdflib.Namespace(nkod_voc)

    g.bind('dcat', dcat)
    g.bind('dcterms', dcterms)
    g.bind('foaf', foaf)
    g.bind('void', void)
    g.bind('vcard', vcard)
    g.bind('schema', schema)
    g.bind('nkod', nkod_voc_ns)

    h = rdflib.ConjunctiveGraph()
    h.parse("nkod-sparql.trig", format="trig")
    for s, p, o in h:
        original_s, original_p, original_o = s, p, o

        s = str(s).replace("\n", "").replace("%3A", "-").replace("%2F", "-")
        p = str(p).replace("\n", "").replace("%3A", "-").replace("%2F", "-")
        if type(o) != rdflib.Literal:
            o = str(o).replace("\n", "").replace("%3A", "-").replace("%2F", "-")

        s = transform(s, nkod_ds, my_ds_ns)
        p = transform(p, nkod_ds, my_ds_ns)
        o = transform(o, nkod_ds, my_ds_ns)

        if p != nkod_voc_ns['ruian_code'] and \
           p != nkod_voc_ns['ruian_type'] and \
           p != nkod_voc_ns['mediaType'] and \
           p != nkod_voc_ns['accrualPeriodicity'] and \
           not ((p == RDF.type) and (o == dcat['CatalogRecord'])) and \
           s != rdflib.URIRef('https://data.gov.cz/zdroj/katalog/NKOD') and \
           p != rdflib.URIRef('https://data.gov.cz/slovník/nkod/typ-úložiště-datové-sady/typÚložiště'):
            g.add( (s, p, o) )

    # najit distribuce bez dcat:mediaType
    #dirty = g.query("SELECT ?a ?c WHERE { ?a a dcat:Distribution. MINUS {?a dcat:mediaType ?b} ?a nkod:mediaType ?c }")
    #for distribution, mediaType in dirty:
        #distribution: URIRef
        #mediaType: Literal

    #    if distribution.endswith("rdf%252bxml"):
    #        g.remove( (distribution, nkod_voc_ns['mediaType'], mediaType) )
    #        g.add( (distribution, nkod_voc_ns['mediaType'], rdflib.Literal('application/rdf+xml')) )
    #        g.add( (distribution, dcat['mediaType'], rdflib.URIRef('http://www.iana.org/assignments/media-types/application/rdf+xml')) )
    #    elif distribution.endswith("void"):
    #        pass  # TODO
    #    elif distribution.endswith("sparql"):
    #        if str(mediaType) == "api/sparql":
    #            pass  # OK
    #        else:
    #            g.remove( (distribution, nkod_voc_ns['mediaType'], mediaType) )
    #            g.add( (distribution, nkod_voc_ns['mediaType'], rdflib.Literal('api/sparql')) )


    # Praha
    g.parse('praha-catalog.ttl', format='turtle')

    # katalogizace
    catalog = rdflib.URIRef('https://data.eghuro.cz/resource/catalog')
    for s, p, o in g.triples( (None, RDF.type, dcat.Dataset) ) :
        g.add( (catalog, dcat.dataset, s) )

    g.parse('my-catalog.ttl', format='turtle')
    g.serialize(format='turtle', destination='dcat-viewer-catalog.ttl')

if __name__ == '__main__':
    convert()
