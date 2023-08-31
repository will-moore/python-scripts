

from cfunits import Units

omero_units = ['ANGSTROM', 'ASTRONOMICALUNIT', 'ATTOMETER', 'CENTIMETER', 'DECAMETER', 'DECIMETER', 'EXAMETER', 'FEMTOMETER', 'FOOT', 'GIGAMETER', 'HECTOMETER', 'INCH', 'KILOMETER', 'LIGHTYEAR', 'LINE', 'MEGAMETER', 'METER', 'MICROMETER', 'MILE', 'MILLIMETER', 'NANOMETER', 'PARSEC', 'PETAMETER', 'PICOMETER', 'POINT', 'TERAMETER', 'THOU', 'YARD', 'YOCTOMETER', 'YOTTAMETER', 'ZEPTOMETER', 'ZETTAMETER']

valid_units = [u.lower() for u in omero_units if Units(u.lower()).isvalid]

print(valid_units)
# for u in omero_units:
#     print(u, Units(u).isvalid)
#     print(u.lower(), Units(u.lower()).isvalid)

time_units = ['ATTOSECOND', 'CENTISECOND', 'DAY', 'DECASECOND', 'DECISECOND', 'EXASECOND', 'FEMTOSECOND', 'GIGASECOND', 'HECTOSECOND', 'HOUR', 'KILOSECOND', 'MEGASECOND', 'MICROSECOND', 'MILLISECOND', 'MINUTE', 'NANOSECOND', 'PETASECOND', 'PICOSECOND', 'SECOND', 'TERASECOND', 'YOCTOSECOND', 'YOTTASECOND', 'ZEPTOSECOND', 'ZETTASECOND']

valid_units = [u.lower() for u in time_units if Units(u.lower()).isvalid]

print(valid_units)
