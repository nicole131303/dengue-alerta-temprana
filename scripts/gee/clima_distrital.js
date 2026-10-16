/**
 * Extracción de clima diario por distrito en Google Earth Engine (code.earthengine.google.com)
 * ------------------------------------------------------------------------------------------
 * Salida: un CSV por año con columnas  ubigeo, fecha, precip_mm, temp_c, rocio_c
 * Fuentes:
 *   - CHIRPS diario (UCSB-CHG/CHIRPS/DAILY): precipitación, ~5.5 km
 *   - ERA5-Land agregado diario (ECMWF/ERA5_LAND/DAILY_AGGR): temperatura y punto de rocío a 2 m
 *
 * Pasos:
 *   1. Subir el shapefile de distritos del INEI como Asset (Assets -> New -> Shape files)
 *      y reemplazar la ruta de DISTRITOS. Debe tener el campo UBIGEO.
 *   2. Ejecutar. En la pestaña "Tasks" aparecerá una exportación por año: pulsar RUN.
 *   3. Descargar los CSV desde Google Drive, unirlos y guardarlos como
 *      data/external/clima_distrital_diario.csv
 */

var DISTRITOS = ee.FeatureCollection('projects/TU_PROYECTO/assets/distritos_inei');
var ANIOS = ee.List.sequence(2009, 2023); // 2009: un año extra para los rezagos iniciales
var CARPETA_DRIVE = 'tesis_dengue_clima';

var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation');
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
  .select(['temperature_2m', 'dewpoint_temperature_2m']);

// Une lluvia y temperatura del mismo día en una sola imagen de 3 bandas
function imagenDelDia(fecha) {
  fecha = ee.Date(fecha);
  var siguiente = fecha.advance(1, 'day');
  var lluvia = chirps.filterDate(fecha, siguiente).first().rename('precip_mm');
  var temp = era5.filterDate(fecha, siguiente).first();
  var tempC = temp.select('temperature_2m').subtract(273.15).rename('temp_c');
  var rocioC = temp.select('dewpoint_temperature_2m').subtract(273.15).rename('rocio_c');
  return lluvia.addBands(tempC).addBands(rocioC).set('fecha', fecha.format('YYYY-MM-dd'));
}

// Promedio espacial de cada banda dentro de cada distrito, para un día
function estadisticasDelDia(fecha) {
  var img = imagenDelDia(fecha);
  return img.reduceRegions({
    collection: DISTRITOS.select(['UBIGEO']),
    reducer: ee.Reducer.mean(),
    scale: 5566, // resolución nativa de CHIRPS
    tileScale: 4,
  }).map(function (f) {
    return ee.Feature(null, {
      ubigeo: f.get('UBIGEO'),
      fecha: img.get('fecha'),
      precip_mm: f.get('precip_mm'),
      temp_c: f.get('temp_c'),
      rocio_c: f.get('rocio_c'),
    });
  });
}

// Una exportación por año (si se pide todo junto, Earth Engine excede sus límites)
ANIOS.evaluate(function (anios) {
  anios.forEach(function (anio) {
    var inicio = ee.Date.fromYMD(anio, 1, 1);
    var nDias = ee.Date.fromYMD(anio + 1, 1, 1).difference(inicio, 'day');
    var dias = ee.List.sequence(0, nDias.subtract(1)).map(function (d) {
      return inicio.advance(d, 'day');
    });
    var tabla = ee.FeatureCollection(dias.map(estadisticasDelDia)).flatten();
    Export.table.toDrive({
      collection: tabla,
      description: 'clima_distrital_' + anio,
      folder: CARPETA_DRIVE,
      fileFormat: 'CSV',
      selectors: ['ubigeo', 'fecha', 'precip_mm', 'temp_c', 'rocio_c'],
    });
  });
});
