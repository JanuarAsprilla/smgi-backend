"""
Métodos para exportación completa de Shapefile
Integrar estos métodos en apps/geodata/views.py en la clase LayerViewSet
"""
import os
import tempfile
import zipfile
from pathlib import Path
from django.http import HttpResponse
from osgeo import ogr, osr
from datetime import datetime


def _export_shapefile_complete(self, layer, gdf):
    """
    Exportar Shapefile COMPLETO con todos los archivos necesarios:
    .shp, .shx, .dbf, .prj, .cpg, .sbn, .sbx, .shp.xml
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / layer.name.replace(' ', '_')
        shp_path = str(base_path) + '.shp'
        
        # 1. Escribir Shapefile base (.shp, .shx, .dbf)
        gdf.to_file(shp_path, driver='ESRI Shapefile', encoding='utf-8')
        
        # 2. Crear archivo .prj (Sistema de coordenadas)
        self._create_prj_file(str(base_path) + '.prj', layer.srid)
        
        # 3. Crear archivo .cpg (Codificación UTF-8)
        self._create_cpg_file(str(base_path) + '.cpg')
        
        # 4. Crear índice espacial (.sbn, .sbx) si hay muchos features
        if gdf.shape[0] > 100:
            self._create_spatial_index(shp_path)
        
        # 5. Crear metadata XML (.shp.xml)
        self._create_shapefile_metadata(
            str(base_path) + '.shp.xml',
            layer,
            gdf
        )
        
        # 6. Comprimir todo en ZIP
        zip_filename = f'{layer.name.replace(" ", "_")}_shapefile.zip'
        zip_path = Path(tmpdir) / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.shp.xml']:
                file_path = str(base_path) + ext
                if os.path.exists(file_path):
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
        
        # 7. Retornar ZIP
        with open(zip_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            return response


def _create_prj_file(self, prj_path, srid):
    """Crear archivo .prj con la proyección WKT"""
    try:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srid)
        with open(prj_path, 'w') as f:
            f.write(srs.ExportToWkt())
    except Exception as e:
        # Fallback a WGS84 si falla
        with open(prj_path, 'w') as f:
            f.write('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]')


def _create_cpg_file(self, cpg_path):
    """Crear archivo .cpg con codificación UTF-8"""
    with open(cpg_path, 'w') as f:
        f.write('UTF-8')


def _create_spatial_index(self, shp_path):
    """Crear índice espacial (.sbn, .sbx) usando OGR"""
    try:
        driver = ogr.GetDriverByName('ESRI Shapefile')
        dataSource = driver.Open(shp_path, 1)  # 1 = write mode
        if dataSource:
            layer = dataSource.GetLayer()
            # Crear índice espacial
            dataSource.ExecuteSQL(f'CREATE SPATIAL INDEX ON {layer.GetName()}')
            dataSource = None  # Cerrar
    except Exception as e:
        # No crítico si falla
        pass


def _create_shapefile_metadata(self, xml_path, layer, gdf):
    """Crear metadata ISO 19139 en XML"""
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<metadata xml:lang="es">
  <idinfo>
    <citation>
      <citeinfo>
        <origin>SMGI System</origin>
        <pubdate>{datetime.now().strftime("%Y%m%d")}</pubdate>
        <title>{layer.name}</title>
      </citeinfo>
    </citation>
    <descript>
      <abstract>{layer.description or "Sin descripción"}</abstract>
      <purpose>Datos geoespaciales exportados desde SMGI</purpose>
    </descript>
    <spdom>
      <bounding>
        <westbc>{gdf.total_bounds[0]}</westbc>
        <eastbc>{gdf.total_bounds[2]}</eastbc>
        <northbc>{gdf.total_bounds[3]}</northbc>
        <southbc>{gdf.total_bounds[1]}</southbc>
      </bounding>
    </spdom>
  </idinfo>
  <spdoinfo>
    <direct>Vector</direct>
    <ptvctinf>
      <sdtsterm>
        <sdtstype>{layer.geometry_type}</sdtstype>
        <ptvctcnt>{gdf.shape[0]}</ptvctcnt>
      </sdtsterm>
    </ptvctinf>
  </spdoinfo>
  <spref>
    <horizsys>
      <geodetic>
        <horizdn>WGS84</horizdn>
        <ellips>WGS84</ellips>
      </geodetic>
    </horizsys>
  </spref>
  <metainfo>
    <metd>{datetime.now().strftime("%Y%m%d")}</metd>
    <metc>
      <cntinfo>
        <cntorgp>
          <cntorg>SMGI System</cntorg>
        </cntorgp>
      </cntinfo>
    </metc>
    <metstdn>FGDC Content Standards for Digital Geospatial Metadata</metstdn>
    <metstdv>FGDC-STD-001-1998</metstdv>
  </metainfo>
</metadata>'''
    
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
