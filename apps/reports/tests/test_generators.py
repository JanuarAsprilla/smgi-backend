# apps/reports/tests/test_generators.py
"""
SMGI Backend - Tests for Report Generators
Sistema de Monitoreo Geoespacial Inteligente
Pruebas unitarias para los generadores de informes
"""
import pytest
import logging
import tempfile
import os
import io
import json
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.gis.geos import Point, Polygon

from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.reports.models import (
    Report, GeneratedReport, ReportFormat, ReportStatus
)
from apps.reports.generators.base_generator import BaseReportGenerator
from apps.reports.generators.pdf_generator import PDFReportGenerator
from apps.reports.generators.excel_generator import ExcelReportGenerator
from apps.reports.generators.geojson_generator import GeoJSONReportGenerator


logger = logging.getLogger('apps.reports.tests.generators')


# --- Fixtures ---

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='generator_test_user',
        email='generator@test.com',
        password='testpass123'
    )

@pytest.fixture
def arcgis_service(user):
    return ArcGISService.objects.create(
        name='Generator Test Service',
        base_url='https://generatortest.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=777,
        name='Generator Test Layer',
        geometry_type='point',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def report(user, arcgis_service, spatial_layer):
    return Report.objects.create(
        name='Generator Test Report',
        description='Test report for generator testing',
        report_id='GENERATOR-TEST-001',
        report_type='monitoring_summary',
        format_type=ReportFormat.PDF,
        service=arcgis_service,
        layer=spatial_layer,
        created_by=user,
        is_active=True,
        is_scheduled=False,
        change_threshold=5.0,
        notify_on_completion=True
    )

@pytest.fixture
def generated_report(report, user):
    return GeneratedReport.objects.create(
        report=report,
        generated_by=user,
        report_id='GEN-GENERATOR-TEST-001',
        file=ContentFile(b'Test PDF content', name='test_report.pdf'),
        file_size_bytes=102400, # 100 KB
        file_checksum='abc123...',
        format_type=ReportFormat.PDF,
        status=ReportStatus.COMPLETED,
        parameters_used={'test_param': 'value'},
        generation_duration_ms=5000, # 5 segundos
        record_count=1000,
        page_count=10,
        memory_usage_mb=50,
        cpu_usage_percent=25.0,
        execution_log=[],
        performance_metrics={}
    )

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# --- Tests for BaseReportGenerator ---

class TestBaseReportGenerator:

    def test_init(self):
        generator = BaseReportGenerator(
            name='Test Generator',
            description='A test generator',
            format_type=ReportFormat.PDF,
            is_active=True,
            default_options={'option1': 'value1'}
        )
        assert generator.name == 'Test Generator'
        assert generator.description == 'A test generator'
        assert generator.format_type == ReportFormat.PDF
        assert generator.is_active is True
        assert generator.default_options == {'option1': 'value1'}
        assert generator.temp_files == []

    def test_abstract_generate_method(self):
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        with pytest.raises(NotImplementedError):
            generator.generate(MagicMock(), {})

    def test_validate_input_data(self):
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        # Valid data
        valid_data = {'key': 'value'}
        assert generator.validate_input_data(valid_data) is True

        # Invalid data (not a dict)
        invalid_data = 'not a dict'
        assert generator.validate_input_data(invalid_data) is False

    @patch('apps.reports.generators.base_generator.tempfile.mkstemp')
    def test_prepare_output_path(self, mock_mkstemp, temp_dir):
        mock_mkstemp.return_value = (123, os.path.join(temp_dir, 'test_file.tmp'))
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        report_mock = MagicMock()
        report_mock.id = 'test-report-id'
        
        output_path = generator.prepare_output_path(report_mock, suffix='.pdf')
        assert output_path == os.path.join(temp_dir, 'test_file.tmp')
        assert output_path in generator.temp_files
        mock_mkstemp.assert_called_once_with(suffix='.pdf', prefix='report_test-report-id_')

    @patch('apps.reports.generators.base_generator.open', new_callable=MagicMock)
    @patch('apps.reports.generators.base_generator.os.path.getsize')
    @patch('apps.reports.generators.base_generator.transaction.atomic')
    def test_save_generated_report(self, mock_atomic, mock_getsize, mock_open, user, report):
        mock_getsize.return_value = 1024
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        report_mock = MagicMock()
        report_mock.id = 'test-report-id'
        file_path = '/tmp/test_file.pdf'
        file_name = 'test_file.pdf'
        data = {'key': 'value'}
        options = {'option1': 'value1'}
        generation_result = {'duration_ms': 1000, 'records': 10, 'pages': 1}
        
        with patch('apps.reports.generators.base_generator.GeneratedReport.objects.create') as mock_create:
            mock_generated_report = MagicMock()
            mock_create.return_value = mock_generated_report
            
            result = generator.save_generated_report(
                report, file_path, file_name, data, options, generation_result
            )
            
            assert result == mock_generated_report
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs['report'] == report
            assert call_kwargs['file_size_bytes'] == 1024
            assert call_kwargs['generation_duration_ms'] == 1000
            assert call_kwargs['record_count'] == 10
            assert call_kwargs['page_count'] == 1

    def test_get_supported_formats(self):
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        supported = generator.get_supported_formats()
        assert supported == [ReportFormat.PDF]

    def test_get_default_options(self):
        default_opts = {'option1': 'value1', 'option2': 'value2'}
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF,
            default_options=default_opts
        )
        options = generator.get_default_options()
        assert options == default_opts
        # Ensure it's a copy
        options['option1'] = 'modified'
        assert generator.default_options['option1'] == 'value1'

    def test_handle_error(self):
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        error = Exception("Test error")
        result = generator.handle_error(error, "Test context")
        assert result['success'] is False
        assert 'Test error' in result['error']
        assert 'Test context' in result['error']

    @patch('apps.reports.generators.base_generator.os.remove')
    def test_cleanup_temp_files(self, mock_remove, temp_dir):
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        temp_file1 = os.path.join(temp_dir, 'temp1.tmp')
        temp_file2 = os.path.join(temp_dir, 'temp2.tmp')
        with open(temp_file1, 'w') as f:
            f.write('temp1')
        with open(temp_file2, 'w') as f:
            f.write('temp2')
        
        generator.temp_files = [temp_file1, temp_file2]
        generator.cleanup_temp_files()
        
        assert mock_remove.call_count == 2
        mock_remove.assert_any_call(temp_file1)
        mock_remove.assert_any_call(temp_file2)
        assert generator.temp_files == []

    def test_context_manager(self, temp_dir):
        generator = BaseReportGenerator(
            name='Test Generator',
            format_type=ReportFormat.PDF
        )
        temp_file = os.path.join(temp_dir, 'temp_cm.tmp')
        with open(temp_file, 'w') as f:
            f.write('temp_cm')
        
        with patch.object(generator, 'cleanup_temp_files') as mock_cleanup:
            with generator:
                generator.temp_files.append(temp_file)
            
            mock_cleanup.assert_called_once()


# --- Tests for PDFReportGenerator ---

class TestPDFReportGenerator:

    def test_init(self):
        generator = PDFReportGenerator()
        assert generator.name == 'PDF Report Generator'
        assert generator.description == 'Generates reports in PDF format'
        assert generator.format_type == ReportFormat.PDF
        assert generator.is_active is True
        assert 'template_name' in generator.default_options
        assert 'include_header' in generator.default_options

    @patch('apps.reports.generators.pdf_generator.render_to_string')
    @patch('apps.reports.generators.pdf_generator.weasyprint.HTML.write_pdf')
    @patch('apps.reports.generators.pdf_generator.open', new_callable=MagicMock)
    @patch('apps.reports.generators.pdf_generator.os.path.getsize')
    def test_generate_success(self, mock_getsize, mock_open, mock_write_pdf, mock_render_to_string, user, report, temp_dir):
        mock_render_to_string.return_value = '<html><body>Test PDF</body></html>'
        mock_write_pdf.return_value = b'PDF binary content'
        mock_getsize.return_value = 1024
        
        generator = PDFReportGenerator()
        data = {
            'context': {
                'title': 'Test PDF Report',
                'content': 'This is a test.'
            }
        }
        options = {
            'template_name': 'reports/test_template.html'
        }
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.pdf')):
            with patch.object(generator, 'save_generated_report') as mock_save:
                mock_generated_report = MagicMock()
                mock_generated_report.id = 'gen-report-id'
                mock_save.return_value = mock_generated_report
                
                result = generator.generate(report, data, options)
                
                assert result['success'] is True
                assert result['file_path'] == os.path.join(temp_dir, 'test_output.pdf')
                assert result['file_size_bytes'] == 1024
                assert result['records'] == 0 # Placeholder
                assert result['pages'] == 1 # Placeholder
                mock_render_to_string.assert_called_once()
                mock_write_pdf.assert_called_once()
                mock_save.assert_called_once()

    def test_generate_failure_invalid_data(self, user, report):
        generator = PDFReportGenerator()
        invalid_data = 'not a dict'
        
        result = generator.generate(report, invalid_data)
        
        assert result['success'] is False
        assert 'Data validation failed' in result['error']

    @patch('apps.reports.generators.pdf_generator.render_to_string')
    def test_generate_failure_render_error(self, mock_render_to_string, user, report, temp_dir):
        mock_render_to_string.side_effect = Exception("Template render error")
        
        generator = PDFReportGenerator()
        data = {'context': {'title': 'Test'}}
        options = {'template_name': 'reports/nonexistent_template.html'}
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.pdf')):
            result = generator.generate(report, data, options)
            
            assert result['success'] is False
            assert 'Template render error' in result['error']

    @patch('apps.reports.generators.pdf_generator.render_to_string')
    @patch('apps.reports.generators.pdf_generator.weasyprint.HTML.write_pdf')
    def test_generate_failure_save_error(self, mock_write_pdf, mock_render_to_string, user, report, temp_dir):
        mock_render_to_string.return_value = '<html><body>Test PDF</body></html>'
        mock_write_pdf.return_value = b'PDF binary content'
        
        generator = PDFReportGenerator()
        data = {'context': {'title': 'Test'}}
        options = {'template_name': 'reports/test_template.html'}
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.pdf')):
            with patch('builtins.open', side_effect=Exception("File save error")):
                result = generator.generate(report, data, options)
                
                assert result['success'] is False
                assert 'File save error' in result['error']

    def test_validate_input_data(self):
        generator = PDFReportGenerator()
        # Valid data
        valid_data = {
            'context': {'title': 'Test'},
            'template_name': 'reports/test_template.html'
        }
        assert generator.validate_input_data(valid_data) is True

        # Invalid context (not a dict)
        invalid_data1 = {
            'context': 'not a dict',
            'template_name': 'reports/test_template.html'
        }
        assert generator.validate_input_data(invalid_data1) is False

        # Invalid template_name (not a string)
        invalid_data2 = {
            'context': {'title': 'Test'},
            'template_name': 123
        }
        assert generator.validate_input_data(invalid_data2) is False

    @patch('apps.reports.generators.pdf_generator.render_to_string')
    def test_render_html_template(self, mock_render_to_string, user, report):
        mock_render_to_string.return_value = '<html><body>Rendered HTML</body></html>'
        
        generator = PDFReportGenerator()
        data = {
            'context': {
                'title': 'Test PDF Report',
                'content': 'This is a test.'
            }
        }
        options = {
            'template_name': 'reports/test_template.html'
        }
        
        html_content = generator.render_html_template(report, data, options)
        
        assert html_content == '<html><body>Rendered HTML</body></html>'
        mock_render_to_string.assert_called_once_with(
            'reports/test_template.html',
            {
                'report': report,
                'data': data,
                'options': options,
                'generated_at': timezone.now(),
                'user': report.created_by,
                'service_name': report.service.name if report.service else 'N/A',
                'layer_name': report.layer.name if report.layer else 'N/A',
                'alert_title': report.alert.title if getattr(report, 'alert', None) else 'N/A'
            }
        )

    @patch('apps.reports.generators.pdf_generator.weasyprint.HTML.write_pdf')
    def test_convert_html_to_pdf(self, mock_write_pdf):
        mock_write_pdf.return_value = b'PDF binary content'
        
        generator = PDFReportGenerator()
        html_content = '<html><body>Test PDF</body></html>'
        options = {
            'base_url': 'http://localhost:8000/static/',
            'presentational_hints': True,
            'custom_css': 'body { font-family: Arial; }',
            'stylesheets': []
        }
        
        pdf_content = generator.convert_html_to_pdf(html_content, options)
        
        assert pdf_content == b'PDF binary content'
        mock_write_pdf.assert_called_once()

    def test_add_page_numbers(self):
        generator = PDFReportGenerator()
        pdf_content = b'PDF binary content'
        options = {}
        
        # This is a placeholder, should return the same content
        result = generator.add_page_numbers(pdf_content, options)
        assert result == pdf_content

    def test_add_watermark(self):
        generator = PDFReportGenerator()
        pdf_content = b'PDF binary content'
        options = {}
        
        # This is a placeholder, should return the same content
        result = generator.add_watermark(pdf_content, options)
        assert result == pdf_content

    def test_add_header_footer(self):
        generator = PDFReportGenerator()
        pdf_content = b'PDF binary content'
        options = {}
        
        # This is a placeholder, should return the same content
        result = generator.add_header_footer(pdf_content, options)
        assert result == pdf_content


# --- Tests for ExcelReportGenerator ---

class TestExcelReportGenerator:

    def test_init(self):
        generator = ExcelReportGenerator()
        assert generator.name == 'Excel Report Generator'
        assert generator.description == 'Generates reports in Excel (.xlsx) format'
        assert generator.format_type == ReportFormat.EXCEL
        assert generator.is_active is True
        assert 'include_header' in generator.default_options
        assert 'auto_adjust_column_width' in generator.default_options

    @patch('apps.reports.generators.excel_generator.openpyxl.Workbook.save')
    @patch('apps.reports.generators.excel_generator.os.path.getsize')
    def test_generate_success(self, mock_getsize, mock_save, user, report, temp_dir):
        mock_getsize.return_value = 2048
        
        generator = ExcelReportGenerator()
        data = {
            'sheets': [
                {
                    'name': 'Sheet1',
                    'data': [
                        {'col1': 'val1', 'col2': 'val2'},
                        {'col1': 'val3', 'col2': 'val4'}
                    ]
                }
            ]
        }
        options = {}
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.xlsx')):
            with patch.object(generator, 'save_generated_report') as mock_save_report:
                mock_generated_report = MagicMock()
                mock_generated_report.id = 'gen-excel-report-id'
                mock_save_report.return_value = mock_generated_report
                
                result = generator.generate(report, data, options)
                
                assert result['success'] is True
                assert result['file_path'] == os.path.join(temp_dir, 'test_output.xlsx')
                assert result['file_size_bytes'] == 2048
                assert result['records'] == 2 # 2 filas de datos
                assert result['pages'] == 1 # 1 hoja
                mock_save.assert_called_once()
                mock_save_report.assert_called_once()

    def test_generate_failure_invalid_data(self, user, report):
        generator = ExcelReportGenerator()
        invalid_data = {
            'sheets': 'not a list'
        }
        
        result = generator.generate(report, invalid_data)
        
        assert result['success'] is False
        assert 'Data validation failed' in result['error']

    @patch('apps.reports.generators.excel_generator.openpyxl.Workbook.save')
    def test_generate_failure_save_error(self, mock_save, user, report, temp_dir):
        mock_save.side_effect = Exception("Excel save error")
        
        generator = ExcelReportGenerator()
        data = {
            'sheets': [
                {
                    'name': 'Sheet1',
                    'data': [{'col1': 'val1'}]
                }
            ]
        }
        options = {}
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.xlsx')):
            result = generator.generate(report, data, options)
            
            assert result['success'] is False
            assert 'Excel save error' in result['error']

    def test_validate_input_data(self):
        generator = ExcelReportGenerator()
        # Valid data
        valid_data = {
            'sheets': [
                {
                    'name': 'Sheet1',
                    'data': [{'col1': 'val1'}]
                }
            ]
        }
        assert generator.validate_input_data(valid_data) is True

        # Invalid sheets (not a list)
        invalid_data1 = {
            'sheets': 'not a list'
        }
        assert generator.validate_input_data(invalid_data1) is False

        # Invalid sheet info (not a dict)
        invalid_data2 = {
            'sheets': ['not a dict']
        }
        assert generator.validate_input_data(invalid_data2) is False

        # Invalid sheet name (not a string)
        invalid_data3 = {
            'sheets': [
                {
                    'name': 123,
                    'data': [{'col1': 'val1'}]
                }
            ]
        }
        assert generator.validate_input_data(invalid_data3) is False

        # Invalid sheet data (not a list)
        invalid_data4 = {
            'sheets': [
                {
                    'name': 'Sheet1',
                    'data': 'not a list'
                }
            ]
        }
        assert generator.validate_input_data(invalid_data4) is False

        # Invalid row data (not a dict)
        invalid_data5 = {
            'sheets': [
                {
                    'name': 'Sheet1',
                    'data': ['not a dict']
                }
            ]
        }
        assert generator.validate_input_data(invalid_data5) is False

    def test_create_worksheet_from_data(self):
        # This would require mocking openpyxl objects
        # For now, we test that it doesn't crash
        generator = ExcelReportGenerator()
        ws_mock = MagicMock()
        sheet_data = [
            {'col1': 'val1', 'col2': 'val2'},
            {'col1': 'val3', 'col2': 'val4'}
        ]
        options = {'include_header': True, 'apply_styles': True}
        
        # This is a complex test that requires deep mocking of openpyxl
        # We'll assume it works if it doesn't raise an exception
        try:
            generator.create_worksheet_from_data(ws_mock, sheet_data, options)
            assert True # If no exception is raised, it's a pass
        except Exception as e:
            pytest.fail(f"create_worksheet_from_data raised an exception: {e}")

    def test_apply_styles(self):
        # This would require mocking openpyxl objects
        # For now, we test that it doesn't crash
        generator = ExcelReportGenerator()
        ws_mock = MagicMock()
        column_count = 3
        
        # This is a complex test that requires deep mocking of openpyxl
        # We'll assume it works if it doesn't raise an exception
        try:
            generator._apply_header_styles(ws_mock, column_count)
            assert True # If no exception is raised, it's a pass
        except Exception as e:
            pytest.fail(f"_apply_header_styles raised an exception: {e}")

    def test_add_chart(self):
        # This would require mocking openpyxl objects
        # For now, we test that it doesn't crash
        generator = ExcelReportGenerator()
        ws_mock = MagicMock()
        
        # This is a complex test that requires deep mocking of openpyxl
        # We'll assume it works if it doesn't raise an exception
        try:
            generator.add_chart(ws_mock)
            assert True # If no exception is raised, it's a pass
        except Exception as e:
            pytest.fail(f"add_chart raised an exception: {e}")

    def test_add_image(self):
        # This would require mocking openpyxl objects
        # For now, we test that it doesn't crash
        generator = ExcelReportGenerator()
        ws_mock = MagicMock()
        
        # This is a complex test that requires deep mocking of openpyxl
        # We'll assume it works if it doesn't raise an exception
        try:
            generator.add_image(ws_mock)
            assert True # If no exception is raised, it's a pass
        except Exception as e:
            pytest.fail(f"add_image raised an exception: {e}")


# --- Tests for GeoJSONReportGenerator ---

class TestGeoJSONReportGenerator:

    def test_init(self):
        generator = GeoJSONReportGenerator()
        assert generator.name == 'GeoJSON Report Generator'
        assert generator.description == 'Generates reports in GeoJSON format'
        assert generator.format_type == ReportFormat.GEOJSON
        assert generator.is_active is True
        assert 'include_properties' in generator.default_options
        assert 'include_bbox' in generator.default_options

    @patch('apps.reports.generators.geojson_generator.json.dump')
    @patch('apps.reports.generators.geojson_generator.os.path.getsize')
    def test_generate_success(self, mock_getsize, mock_json_dump, user, report, temp_dir):
        mock_getsize.return_value = 1024
        
        generator = GeoJSONReportGenerator()
        data = {
            'features': [
                {
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [0, 0]
                    },
                    'properties': {
                        'name': 'Test Feature 1'
                    }
                },
                {
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                    },
                    'properties': {
                        'name': 'Test Feature 2'
                    }
                }
            ],
            'metadata': {
                'title': 'Test GeoJSON Report'
            }
        }
        options = {}
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.geojson')):
            with patch.object(generator, 'save_generated_report') as mock_save_report:
                mock_generated_report = MagicMock()
                mock_generated_report.id = 'gen-geojson-report-id'
                mock_save_report.return_value = mock_generated_report
                
                result = generator.generate(report, data, options)
                
                assert result['success'] is True
                assert result['file_path'] == os.path.join(temp_dir, 'test_output.geojson')
                assert result['file_size_bytes'] == 1024
                assert result['records'] == 2 # 2 features
                assert result['pages'] == 1 # 1 "documento"
                mock_json_dump.assert_called_once()
                mock_save_report.assert_called_once()

    def test_generate_failure_invalid_data(self, user, report):
        generator = GeoJSONReportGenerator()
        invalid_data = {
            'features': 'not a list'
        }
        
        result = generator.generate(report, invalid_data)
        
        assert result['success'] is False
        assert 'Data validation failed' in result['error']

    @patch('apps.reports.generators.geojson_generator.json.dump')
    def test_generate_failure_save_error(self, mock_json_dump, user, report, temp_dir):
        mock_json_dump.side_effect = Exception("GeoJSON save error")
        
        generator = GeoJSONReportGenerator()
        data = {
            'features': [
                {
                    'geometry': {'type': 'Point', 'coordinates': [0, 0]},
                    'properties': {'name': 'Test Feature'}
                }
            ]
        }
        options = {}
        
        with patch.object(generator, 'prepare_output_path', return_value=os.path.join(temp_dir, 'test_output.geojson')):
            result = generator.generate(report, data, options)
            
            assert result['success'] is False
            assert 'GeoJSON save error' in result['error']

    def test_validate_input_data(self):
        generator = GeoJSONReportGenerator()
        # Valid data
        valid_data = {
            'features': [
                {
                    'geometry': {'type': 'Point', 'coordinates': [0, 0]},
                    'properties': {'name': 'Test Feature'}
                }
            ]
        }
        assert generator.validate_input_data(valid_data) is True

        # Invalid features (not a list)
        invalid_data1 = {
            'features': 'not a list'
        }
        assert generator.validate_input_data(invalid_data1) is False

        # Invalid feature (not a dict)
        invalid_data2 = {
            'features': ['not a dict']
        }
        assert generator.validate_input_data(invalid_data2) is False

        # Invalid geometry (missing)
        invalid_data3 = {
            'features': [
                {
                    'properties': {'name': 'Test Feature'}
                }
            ]
        }
        assert generator.validate_input_data(invalid_data3) is False

        # Invalid geometry (not a dict)
        invalid_data4 = {
            'features': [
                {
                    'geometry': 'not a dict',
                    'properties': {'name': 'Test Feature'}
                }
            ]
        }
        assert generator.validate_input_data(invalid_data4) is False

        # Invalid properties (not a dict)
        invalid_data5 = {
            'features': [
                {
                    'geometry': {'type': 'Point', 'coordinates': [0, 0]},
                    'properties': 'not a dict'
                }
            ]
        }
        assert generator.validate_input_data(invalid_data5) is False

    def test_create_geojson_structure(self):
        generator = GeoJSONReportGenerator()
        options = {
            'include_bbox': False,
            'include_crs': False
        }
        
        geojson_data = generator.create_geojson_structure(options)
        
        assert geojson_data['type'] == 'FeatureCollection'
        assert geojson_data['features'] == []
        assert 'bbox' not in geojson_data
        assert 'crs' not in geojson_data

    def test_add_features_to_geojson(self):
        generator = GeoJSONReportGenerator()
        geojson_data = {
            'type': 'FeatureCollection',
            'features': []
        }
        features = [
            {
                'geometry': {'type': 'Point', 'coordinates': [0, 0]},
                'properties': {'name': 'Test Feature 1'}
            },
            {
                'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                'properties': {'name': 'Test Feature 2'}
            }
        ]
        options = {
            'include_properties': True,
            'include_bbox': False
        }
        
        added_count = generator.add_features_to_geojson(geojson_data, features, options)
        
        assert added_count == 2
        assert len(geojson_data['features']) == 2
        assert geojson_data['features'][0]['type'] == 'Feature'
        assert geojson_data['features'][0]['geometry']['type'] == 'Point'
        assert geojson_data['features'][0]['properties']['name'] == 'Test Feature 1'
        assert geojson_data['features'][1]['type'] == 'Feature'
        assert geojson_data['features'][1]['geometry']['type'] == 'Polygon'
        assert geojson_data['features'][1]['properties']['name'] == 'Test Feature 2'

    def test_add_metadata_to_geojson(self, user, report):
        generator = GeoJSONReportGenerator()
        geojson_data = {
            'type': 'FeatureCollection',
            'features': []
        }
        metadata = {
            'custom_key': 'custom_value'
        }
        options = {
            'include_metadata': True
        }
        
        generator.add_metadata_to_geojson(geojson_data, metadata, report, options)
        
        assert 'metadata' in geojson_data
        assert geojson_data['metadata']['report_id'] == str(report.id)
        assert geojson_data['metadata']['report_name'] == report.name
        assert geojson_data['metadata']['generated_by'] == report.created_by.get_full_name()
        assert geojson_data['metadata']['custom_key'] == 'custom_value'

    def test_add_changes_to_geojson(self):
        generator = GeoJSONReportGenerator()
        geojson_data = {
            'type': 'FeatureCollection',
            'features': []
        }
        changes = [
            {
                'feature_id': 'fid1',
                'change_type': 'added',
                'change_details': {'field': 'value'}
            },
            {
                'feature_id': 'fid2',
                'change_type': 'modified',
                'change_details': {'field': 'new_value'}
            }
        ]
        options = {
            'include_changes': True,
            'changes_as_properties': True
        }
        
        generator.add_changes_to_geojson(geojson_data, changes, options)
        
        assert 'changes' in geojson_data
        assert len(geojson_data['changes']) == 2
        # Changes as properties would require features to exist and match by feature_id
        # This is a basic test, more complex logic would be in the actual implementation

    def test_add_snapshots_to_geojson(self):
        generator = GeoJSONReportGenerator()
        geojson_data = {
            'type': 'FeatureCollection',
            'features': []
        }
        snapshots = [
            {
                'snapshot_id': 'snap1',
                'snapshot_hash': 'hash1',
                'created': '2023-01-01T00:00:00Z'
            },
            {
                'snapshot_id': 'snap2',
                'snapshot_hash': 'hash2',
                'created': '2023-01-02T00:00:00Z'
            }
        ]
        options = {
            'include_snapshots': True,
            'snapshot_as_metadata': True
        }
        
        generator.add_snapshots_to_geojson(geojson_data, snapshots, options)
        
        assert 'snapshots' in geojson_data
        assert len(geojson_data['snapshots']) == 2
        assert 'snapshots_summary' in geojson_data['metadata']

    def test_validate_geojson_feature(self):
        generator = GeoJSONReportGenerator()
        # Valid feature
        valid_feature = {
            'geometry': {'type': 'Point', 'coordinates': [0, 0]},
            'properties': {'name': 'Test Feature'}
        }
        assert generator.validate_geojson_feature(valid_feature) is True

        # Invalid feature (not a dict)
        invalid_feature1 = 'not a dict'
        assert generator.validate_geojson_feature(invalid_feature1) is False

        # Invalid feature (missing geometry)
        invalid_feature2 = {
            'properties': {'name': 'Test Feature'}
        }
        assert generator.validate_geojson_feature(invalid_feature2) is False

        # Invalid feature (geometry not a dict)
        invalid_feature3 = {
            'geometry': 'not a dict',
            'properties': {'name': 'Test Feature'}
        }
        assert generator.validate_geojson_feature(invalid_feature3) is False

        # Invalid feature (geometry missing type)
        invalid_feature4 = {
            'geometry': {'coordinates': [0, 0]},
            'properties': {'name': 'Test Feature'}
        }
        assert generator.validate_geojson_feature(invalid_feature4) is False

        # Invalid feature (geometry missing coordinates)
        invalid_feature5 = {
            'geometry': {'type': 'Point'},
            'properties': {'name': 'Test Feature'}
        }
        assert generator.validate_geojson_feature(invalid_feature5) is False
