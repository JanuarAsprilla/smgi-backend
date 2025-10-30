# apps/reports/generators/pdf_generator.py
"""
SMGI Backend - PDF Report Generator
Sistema de Monitoreo Geoespacial Inteligente
Generador de informes en formato PDF
"""
import logging
import io
import time
import os
from typing import Dict, Any, Optional, List, Union
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.conf import settings

# Biblioteca para generar PDF
# Opción 1: WeasyPrint (más fácil de usar, mejor CSS)
try:
    import weasyprint
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False
    weasyprint = None

# Opción 2: ReportLab (más control, más complejo)
# try:
#     import reportlab
#     from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
#     from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
#     from reportlab.lib.units import inch
#     from reportlab.lib.pagesizes import letter, A4
#     from reportlab.lib import colors
#     HAS_REPORTLAB = True
# except ImportError:
#     HAS_REPORTLAB = False
#     reportlab = None

from apps.reports.generators.base_generator import BaseReportGenerator
from apps.reports.models import Report, GeneratedReport, ReportFormat, ReportStatus


logger = logging.getLogger('apps.reports.generators.pdf')


class PDFReportGenerator(BaseReportGenerator):
    """
    Generador de informes en formato PDF usando WeasyPrint.
    """

    def __init__(
        self,
        name: str = "PDF Report Generator",
        description: str = "Generates reports in PDF format",
        is_active: bool = True,
        default_options: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa el generador de informes PDF.

        Args:
            name (str): Nombre del generador.
            description (str): Descripción del generador.
            is_active (bool): Indica si el generador está activo.
            default_options (Optional[Dict[str, Any]]): Opciones por defecto.
        """
        if not HAS_WEASYPRINT:
            raise ImportError("weasyprint is required to use PDFReportGenerator. Please install it: pip install weasyprint")
        
        super().__init__(
            name=name,
            description=description,
            format_type=ReportFormat.PDF,
            is_active=is_active,
            default_options=default_options or {
                'template_name': 'reports/default_pdf_report.html',
                'include_header': True,
                'include_footer': True,
                'include_page_numbers': True,
                'include_watermark': False,
                'watermark_text': 'CONFIDENTIAL',
                'page_size': 'A4',
                'orientation': 'portrait',
                'margin_top': '1cm',
                'margin_bottom': '1cm',
                'margin_left': '1cm',
                'margin_right': '1cm',
                'stylesheets': [], # Lista de rutas a hojas de estilo CSS adicionales
                'base_url': getattr(settings, 'STATIC_URL', '/static/'), # Base URL for relative links
                'presentational_hints': True, # Interpretar atributos HTML de estilo (bgcolor, align, etc.)
                'optimize_images': True,
                'dpi': 96, # Resolución de imagen
                'zoom': 1.0, # Zoom factor
                'custom_css': '' # CSS personalizado en línea
            }
        )
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def generate(self, report: Report, data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera un informe en formato PDF.

        Args:
            report (Report): Instancia del modelo Report que se está generando.
            data (Dict[str, Any]): Datos para generar el informe.
                                   Puede incluir 'context' para pasar a la plantilla.
            options (Optional[Dict[str, Any]]): Opciones específicas para esta generación.

        Returns:
            Dict[str, Any]: Resultado de la generación.
        """
        start_time = time.time()
        self.logger.info(f"Starting PDF report generation for {report.name}")
        
        # Merge options
        merged_options = self.default_options.copy()
        if options:
            merged_options.update(options)
        
        try:
            # Validate input data
            if not self.validate_input_data(data):
                return self.handle_error(ValueError("Invalid input data"), "Data validation failed")
            
            # Prepare output path
            output_path = self.prepare_output_path(report, suffix='.pdf')
            
            # Render HTML template
            html_content = self.render_html_template(report, data, merged_options)
            
            # Convert HTML to PDF
            pdf_content = self.convert_html_to_pdf(html_content, merged_options)
            
            # Save PDF to file
            with open(output_path, 'wb') as f:
                f.write(pdf_content)
            
            # Get file size
            file_size_bytes = os.path.getsize(output_path)
            
            # Estimate page count (rough estimate based on content size)
            # WeasyPrint no proporciona directamente el número de páginas
            # Se puede estimar o usar una biblioteca como PyPDF2 para contar páginas
            try:
                import PyPDF2
                with open(output_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    page_count = len(reader.pages)
            except ImportError:
                # Fallback estimation (very rough)
                # Asumir ~50KB por página A4 con texto normal
                estimated_page_size_kb = 50
                page_count = max(1, round(file_size_bytes / (estimated_page_size_kb * 1024)))
                self.logger.warning("PyPDF2 not installed. Page count is estimated.")
            except Exception as e:
                self.logger.warning(f"Could not determine page count: {e}. Using estimation.")
                estimated_page_size_kb = 50
                page_count = max(1, round(file_size_bytes / (estimated_page_size_kb * 1024)))
            
            # Calculate record count (features, items, etc.)
            record_count = data.get('record_count', 0) # Debe venir en data o calcularse
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.logger.info(f"PDF report generated successfully for {report.name} in {duration_ms} ms")
            
            return {
                'success': True,
                'file_path': output_path,
                'file_size_bytes': file_size_bytes,
                'duration_ms': duration_ms,
                'records': record_count,
                'pages': page_count,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Error generating PDF report for {report.name}: {e}"
            self.logger.error(error_msg)
            return self.handle_error(e, "PDF generation failed")
        finally:
            # Cleanup temp files (handled by context manager or explicit call)
            # self.cleanup_temp_files() # No es necesario llamarlo aquí si se usa context manager
            pass

    def render_html_template(self, report: Report, data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """
        Renderiza una plantilla HTML con el contexto proporcionado.

        Args:
            report (Report): Instancia del modelo Report.
            data (Dict[str, Any]): Datos para pasar a la plantilla.
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            str: Contenido HTML renderizado.
        """
        try:
            template_name = options.get('template_name', self.default_options['template_name'])
            
            # Prepare context
            context = {
                'report': report,
                'data': data,
                'options': options,
                'generated_at': timezone.now(),
                'user': getattr(report, 'created_by', None),
                'service_name': report.service.name if report.service else 'N/A',
                'layer_name': report.layer.name if report.layer else 'N/A',
                'alert_title': report.alert.title if report.alert else 'N/A',
                # Añadir más contexto según sea necesario
            }
            
            # Merge with data context if provided
            data_context = data.get('context', {})
            context.update(data_context)
            
            html_content = render_to_string(template_name, context)
            
            self.logger.debug(f"HTML template {template_name} rendered successfully")
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error rendering HTML template {template_name}: {e}")
            raise

    def convert_html_to_pdf(self, html_content: str, options: Dict[str, Any]) -> bytes:
        """
        Convierte contenido HTML a PDF usando WeasyPrint.

        Args:
            html_content (str): Contenido HTML a convertir.
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            bytes: Contenido del PDF en bytes.
        """
        try:
            # Prepare WeasyPrint HTML object
            base_url = options.get('base_url', self.default_options['base_url'])
            presentational_hints = options.get('presentational_hints', self.default_options['presentational_hints'])
            
            html_doc = weasyprint.HTML(
                string=html_content,
                base_url=base_url,
                presentational_hints=presentational_hints
            )
            
            # Prepare stylesheets
            stylesheets = []
            custom_css = options.get('custom_css', self.default_options['custom_css'])
            if custom_css:
                stylesheets.append(weasyprint.CSS(string=custom_css))
            
            additional_stylesheets = options.get('stylesheets', self.default_options['stylesheets'])
            for stylesheet_path in additional_stylesheets:
                try:
                    stylesheets.append(weasyprint.CSS(filename=stylesheet_path))
                except Exception as e:
                    self.logger.warning(f"Could not load stylesheet {stylesheet_path}: {e}")
            
            # Prepare PDF options
            optimize_images = options.get('optimize_images', self.default_options['optimize_images'])
            dpi = options.get('dpi', self.default_options['dpi'])
            zoom = options.get('zoom', self.default_options['zoom'])
            
            # Generate PDF
            pdf_doc = html_doc.write_pdf(
                stylesheets=stylesheets or None,
                optimize_images=optimize_images,
                resolution=dpi,
                zoom=zoom
            )
            
            self.logger.debug("HTML converted to PDF successfully")
            return pdf_doc # bytes
            
        except Exception as e:
            self.logger.error(f"Error converting HTML to PDF: {e}")
            raise

    def add_page_numbers(self, pdf_content: bytes, options: Dict[str, Any]) -> bytes:
        """
        Añade números de página al PDF.
        WeasyPrint no tiene soporte directo para esto, pero se puede hacer con CSS o manipulación posterior.
        Esta es una implementación básica usando CSS.

        Args:
            pdf_content (bytes): Contenido del PDF.
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            bytes: Contenido del PDF con números de página.
        """
        # Esta función es un placeholder.
        # La forma más efectiva de añadir números de página con WeasyPrint
        # es hacerlo directamente en la plantilla HTML/CSS usando @page y content: counter(page).
        # Ejemplo en CSS:
        # @page {
        #   @bottom-center {
        #     content: "Page " counter(page) " of " counter(pages);
        #   }
        # }
        # Si se requiere manipulación posterior, se podría usar PyPDF2 o pdfrw.
        # Por ahora, se asume que se hace en la plantilla.
        self.logger.info("Page numbering is handled via CSS in the HTML template.")
        return pdf_content

    def add_watermark(self, pdf_content: bytes, options: Dict[str, Any]) -> bytes:
        """
        Añade una marca de agua al PDF.
        WeasyPrint no tiene soporte directo para esto, pero se puede hacer con CSS o manipulación posterior.
        Esta es una implementación básica usando CSS.

        Args:
            pdf_content (bytes): Contenido del PDF.
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            bytes: Contenido del PDF con marca de agua.
        """
        # Esta función es un placeholder.
        # La forma más efectiva de añadir marca de agua con WeasyPrint
        # es hacerlo directamente en la plantilla HTML/CSS usando position: fixed y opacity.
        # Ejemplo en CSS:
        # .watermark {
        #   position: fixed;
        #   top: 50%;
        #   left: 50%;
        #   transform: translate(-50%, -50%) rotate(-45deg);
        #   opacity: 0.1;
        #   font-size: 5em;
        #   color: black;
        #   pointer-events: none;
        #   z-index: 1000;
        # }
        # Si se requiere manipulación posterior, se podría usar PyPDF2 o pdfrw.
        # Por ahora, se asume que se hace en la plantilla.
        self.logger.info("Watermarking is handled via CSS in the HTML template.")
        return pdf_content

    def add_header_footer(self, pdf_content: bytes, options: Dict[str, Any]) -> bytes:
        """
        Añade encabezado y pie de página al PDF.
        WeasyPrint no tiene soporte directo para esto, pero se puede hacer con CSS o manipulación posterior.
        Esta es una implementación básica usando CSS.

        Args:
            pdf_content (bytes): Contenido del PDF.
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            bytes: Contenido del PDF con encabezado y pie de página.
        """
        # Esta función es un placeholder.
        # La forma más efectiva de añadir encabezado y pie de página con WeasyPrint
        # es hacerlo directamente en la plantilla HTML/CSS usando @page y content.
        # Ejemplo en CSS:
        # @page {
        #   @top-center {
        #     content: "SMGI Report - " attr(title);
        #   }
        #   @bottom-center {
        #     content: "Page " counter(page) " of " counter(pages);
        #   }
        # }
        # Si se requiere manipulación posterior, se podría usar PyPDF2 o pdfrw.
        # Por ahora, se asume que se hace en la plantilla.
        self.logger.info("Header/Footer is handled via CSS in the HTML template.")
        return pdf_content

    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """
        Valida los datos de entrada específicos para generación de PDF.

        Args:
            data (Dict[str, Any]): Datos para validar.

        Returns:
            bool: True si los datos son válidos, False en caso contrario.
        """
        # Llamar al método de validación base
        if not super().validate_input_data(data):
            return False
        
        # Validación específica para PDF: verificar contexto
        context = data.get('context')
        if context is not None and not isinstance(context, dict):
            self.logger.error("PDF generator expects 'context' to be a dictionary.")
            return False
        
        # Validar que template_name sea una cadena si se proporciona
        template_name = data.get('template_name') or self.default_options.get('template_name')
        if not isinstance(template_name, str):
            self.logger.error("PDF generator expects 'template_name' to be a string.")
            return False
        
        return True
