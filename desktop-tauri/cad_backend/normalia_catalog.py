"""Curated, explicitly sourced nominal dimensions of standard hardware.

A catalogue MATCH is a geometric candidate, not a purchased part, material,
strength class, thread verification, manufacturing route or price.
All dimensions are nominal millimetres. No fuzzy or volume-only identity.
References (dimension tables, not executable code or imported licences):
  ISO 4014/4017: https://mechcodex.com/reference/hex-bolt-dimensions-metric
  ISO 4762: https://mechcodex.com/reference/socket-head-cap-screw-sizes
  ISO 4032: https://www.wermac.org/bolts/dimensions_hex-nuts_across-flats-and-heights_din-iso.html
  ISO 7089: https://easco.in/images/WEB-PLAIN-WASHER.pdf
  ISO 15: https://cballast.com/documents/deep-groove-ball-bearing-dimensions
  DIN 471: https://mechcodex.com/reference/retaining-ring-sizes-external
Pins ISO 2338: only nominal diameter and nominal length candidates are stored.
Never infer pin tolerances or a DIN/ISO grade from this geometry.
"""
import functools

# Thread diameter -> hex AF and nominal head height.
HEX_HEAD = {4:(7,2.8), 5:(8,3.5), 6:(10,4), 8:(13,5.3),
            10:(16,6.4), 12:(18,7.5), 14:(21,8.8),
            16:(24,10), 20:(30,12.5), 24:(36,15)}
SOCKET_HEAD = {3:(5.5,3), 4:(7,4), 5:(8.5,5), 6:(10,6),
               8:(13,8), 10:(16,10), 12:(18,12), 14:(21,14),
               16:(24,16), 20:(30,20), 24:(36,24)}
# Hex nut nominal reference height is a range in product standards. The table
# records published nominal MAX height, not a geometry acceptance tolerance.
HEX_NUT = {3:(5.5,2.4), 4:(7,3.2), 5:(8,4.7),
           6:(10,5.2), 8:(13,6.8), 10:(16,8.4),
           12:(18,10.8), 14:(21,12.8), 16:(24,14.8),
           20:(30,18), 24:(36,21.5)}
# d1 (hole), d2 (OD), s (thickness).
WASHER = {3:(3.2,7,.5), 4:(4.3,9,.8), 5:(5.3,10,1),
          6:(6.4,12,1.6), 8:(8.4,16,1.6),
          10:(10.5,20,2), 12:(13,24,2.5),
          14:(15,28,2.5), 16:(17,30,3),
          18:(19,34,3), 20:(21,37,3),
          24:(25,44,4), 30:(31,56,4)}
# Bore, outer diameter, width (ISO 15).
BEARING = {
    '6000':(10,26,8), '6001':(12,28,8), '6002':(15,32,9),
    '6003':(17,35,10), '6004':(20,42,12), '6005':(25,47,12),
    '6006':(30,55,13), '6007':(35,62,14), '6008':(40,68,15),
    '6200':(10,30,9), '6201':(12,32,10), '6202':(15,35,11),
    '6203':(17,40,12), '6204':(20,47,14), '6205':(25,52,15),
    '6206':(30,62,16), '6207':(35,72,17), '6208':(40,80,18),
    '6300':(10,35,11), '6301':(12,37,12), '6302':(15,42,13),
    '6303':(17,47,14), '6304':(20,52,15), '6305':(25,62,17),
    '6306':(30,72,19),
}
# Shafts, ring thickness, compatible shaft GROOVE diameter. The ring itself
# has a split and lugs; a simple closed annulus must never match DIN 471.
CIRCLIP = {8:(.8,7.6),10:(1,9.6),12:(1,11.5),15:(1,14.3),
           17:(1,16.2),20:(1.2,19),25:(1.2,23.9),
           30:(1.5,28.6),35:(1.5,33),40:(1.75,37.5),
           45:(1.75,42.5),50:(2,47),60:(2,57)}
# DIN 71412 A reference (Bollhoff/KIPP): thread, wrench AF, overall length.
# CAD often simplifies grease fittings; an unverified length must never
# be silently promoted into an exact DIN catalogue match.
GREASE_NIPPLE = {'M6x1':(6,7,16), 'M8x1':(8,9,16),
                 'M10x1':(10,11,16)}
PIN_DIAMETERS = (2,2.5,3,4,5,6,8,10,12,16,20)
PIN_LENGTHS = (6,8,10,12,14,16,18,20,25,30,35,40,45,50,55,60,70,80,100)
BOLT_LENGTHS = (6,8,10,12,14,16,18,20,25,30,35,40,45,50,55,60,70,80,90,95,100,110,120)

SOURCES={
    'hex-head':'ISO 4014 / ISO 4017',
    'socket-head':'ISO 4762',
    'hex-nut':'ISO 4032',
    'washer':'ISO 7089',
    'bearing':'ISO 15',
    'dowel-pin':'ISO 2338 (nominal sizing only)',
    'circlip':'DIN 471 (shaft ring)',
    'grease-nipple':'DIN 71412 A (reference geometry, not verified type)',
}

@functools.lru_cache(maxsize=1)
def normalia_catalog():
    rows=[]
    def add(family,designation,size,dims,matchable=True):
        rows.append({'id':family+':'+designation,
                     'family':family,'designation':designation,
                     'standard':SOURCES[family], 'size':size,
                     'dimensionsMm':dims,'geometricMatchingAvailable':matchable,
                     'status':'nominal-catalogue-entry'})
    for d,(s,k) in HEX_HEAD.items():
        for length in BOLT_LENGTHS:
            if length>=d:
                add('hex-head',f'M{d}x{length}',f'M{d}',
                    {'threadDiameter':d,'acrossFlats':s,'headHeight':k,'underheadLength':length})
    for d,(dk,k) in SOCKET_HEAD.items():
        for length in BOLT_LENGTHS:
            if length>=d:
                add('socket-head',f'M{d}x{length}',f'M{d}',
                    {'threadDiameter':d,'headDiameter':dk,'headHeight':k,'underheadLength':length})
    for d,(s,m) in HEX_NUT.items():
        add('hex-nut',f'M{d}',f'M{d}',
            {'holeNominal':d,'acrossFlats':s,'heightReferenceMax':m})
    for d,(hole,outer,thickness) in WASHER.items():
        add('washer',f'M{d}',f'M{d}',
            {'innerDiameter':hole,'outerDiameter':outer,'thickness':thickness})
    for number,(inner,outer,width) in BEARING.items():
        add('bearing',number,number,
            {'innerDiameter':inner,'outerDiameter':outer,'width':width})
    for name,(thread_d,flats,nominal_length) in GREASE_NIPPLE.items():
        add('grease-nipple',name,name,
            {'threadDiameter':thread_d,'acrossFlats':flats,
             'overallLengthReference':nominal_length},matchable=False)
    for diameter in PIN_DIAMETERS:
        for length in PIN_LENGTHS:
            if length>=diameter:
                add('dowel-pin',f'{diameter}x{length}',str(diameter),
                    {'diameter':diameter,'length':length})
    for diameter,(thickness,groove) in CIRCLIP.items():
        add('circlip',str(diameter),str(diameter),
            {'shaftDiameter':diameter,'thickness':thickness,'grooveDiameter':groove},
            matchable=False)
    return tuple(rows)


def catalog_summary():
    rows=normalia_catalog()
    families={}
    for row in rows: families[row['family']]=families.get(row['family'],0)+1
    return {'entries':len(rows), 'families':families,
            'limitations':'Nominal sizes, not certificates or part identifiers'}


def lookup_dimensions(family, dimensions):
    """Deterministic dimension lookup, strictly numeric and without naming hacks.

    Callers must independently establish the correct B-Rep topology/family.
    These are *candidate* size matches, not exact manufactured tolerances.
    """
    if family not in SOURCES or not isinstance(dimensions,dict):
        return []
    matches=[]
    for row in normalia_catalog():
        if row['family']!=family or not row['geometricMatchingAvailable']:
            continue
        target=row['dimensionsMm']
        if not dimensions or not set(dimensions).issubset(target):
            continue
        if all(type(v) in (int,float) and v>0 and abs(target[key]-v)<=.02
               for key,v in dimensions.items()):
            matches.append({'designation':row['designation'],
                            'family':family,'standard':row['standard'],
                            'id':row['id']})
    return matches
