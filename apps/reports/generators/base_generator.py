# apps/reports/generators/base_generator.py
"""
SMGI Backend - Base Report Generator
Sistema de Monitoreo Geoespacial Inteligente
Clase base abstracta para generadores de informes
"""
import abc
import logging
import os
import tempfile
import uuid
from typing import Dict, Any, Optional, Union, BinaryIO
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile
from django.db import transaction

from apps.reports.models import Report, GeneratedReport, ReportFormat, ReportStatus

logger = logging.getLogger('apps.reports.generators')


class BaseReportGenerator(abc.ABC):
    """
    Clase base abstracta para todos los generadores de informes.
    Define la interfaz común que deben implementar los generadores específicos.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        format_type: str = ReportFormat.PDF,
        is_active: bool = True,
        default_options: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa el generador base.

        Args:
            name (str): Nombre del generador.
            description (str): Descripción del generador.
            format_type (str): Tipo de formato que genera (PDF, Excel, etc.).
            is_active (bool): Indica si el generador está activo.
            default_options (Optional[Dict[str, Any]]): Opciones por defecto para la generación.
        """
        self.name = name
        self.description = description
        self.format_type = format_type
        self.is_active = is_active
        self.default_options = default_options or {}
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self.temp_files = [] # Lista para rastrear archivos temporales

    @abc.abstractmethod
    def generate(self, report: Report, data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Método abstracto para generar el informe.
        Debe ser implementado por las subclases.

        Args:
            report (Report): Instancia del modelo Report que se está generando.
            data (Dict[str, Any]): Datos para generar el informe.
            options (Optional[Dict[str, Any]]): Opciones específicas para esta generación.

        Returns:
            Dict[str, Any]: Diccionario con resultado de la generación.
                           Debe incluir al menos {'success': bool, 'file_path': str, 'file_size_bytes': int}.
                           Puede incluir 'error', 'duration_ms', 'pages', 'records', etc.
        """
        pass

    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """
        Valida los datos de entrada antes de la generación.
        Puede ser sobreescrito por subclases para validaciones específicas.

        Args:
            data (Dict[str, Any]): Datos para validar.

        Returns:
            bool: True si los datos son válidos, False en caso contrario.
        """
        if not isinstance(data, dict):
            self.logger.error("Input data must be a dictionary.")
            return False

        # Validación básica: requerir 'report_data'
        if 'report_data' not in data:
            self.logger.warning("Missing 'report_data' key in input data.")
            # No es un error crítico, solo una advertencia
        
        return True

    def prepare_output_path(self, report: Report, suffix: str = '.tmp') -> str:
        """
        Prepara la ruta de salida para el archivo generado.
        Crea un archivo temporal y lo agrega a la lista de archivos temporales.

        Args:
            report (Report): Instancia del modelo Report.
            suffix (str): Sufijo para el archivo temporal (incluyendo el punto). Por defecto '.tmp'.

        Returns:
            str: Ruta del archivo temporal creado.
        """
        try:
            # Crear archivo temporal
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=f'report_{report.id}_')
            os.close(temp_fd) # Cerrar el descriptor de archivo, solo necesitamos la ruta
            
            # Añadir a la lista de archivos temporales para limpieza posterior
            self.temp_files.append(temp_path)
            
            self.logger.debug(f"Temporary file created at: {temp_path}")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Error preparing output path: {e}")
            raise

    def save_generated_report(
        self,
        report: Report,
        file_path: str,
        file_name: str,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        generation_result: Optional[Dict[str, Any]] = None
    ) -> GeneratedReport:
        """
        Guarda el informe generado en la base de datos como GeneratedReport.

        Args:
            report (Report): Instancia del modelo Report.
            file_path (str): Ruta del archivo generado.
            file_name (str): Nombre del archivo generado.
            data (Dict[str, Any]): Datos usados para la generación.
            options (Optional[Dict[str, Any]]): Opciones usadas para la generación.
            generation_result (Optional[Dict[str, Any]]): Resultado de la generación (duración, páginas, etc.).

        Returns:
            GeneratedReport: Instancia del modelo GeneratedReport creada.
        """
        try:
            self.logger.info(f"Saving generated report for {report.name}")
            
            # Leer contenido del archivo
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Calcular tamaño y checksum
            file_size_bytes = len(file_content)
            import hashlib
            file_checksum = hashlib.sha256(file_content).hexdigest()
            
            # Preparar datos para el modelo GeneratedReport
            generated_report_data = {
                'report': report,
                'generated_by': getattr(report, 'created_by', None), # Asumir que Report tiene created_by
                'report_id': str(uuid.uuid4()), # Generar un ID único para este informe generado
                'file': ContentFile(file_content, name=file_name),
                'file_size_bytes': file_size_bytes,
                'file_checksum': file_checksum,
                'format_type': self.format_type,
                'status': ReportStatus.COMPLETED,
                'parameters_used': options or {},
                'generation_duration_ms': generation_result.get('duration_ms', 0) if generation_result else 0,
                'record_count': generation_result.get('records', 0) if generation_result else 0,
                'page_count': generation_result.get('pages', 0) if generation_result else 0,
                'memory_usage_mb': generation_result.get('memory_mb', 0) if generation_result else 0,
                'cpu_usage_percent': generation_result.get('cpu_percent', 0) if generation_result else 0,
                'error_message': '', # No hay error si se llegó hasta aquí
                'notification_sent': False, # Se enviará después
                'is_complete': True,
                'is_failed': False
            }
            
            # Crear instancia de GeneratedReport
            with transaction.atomic():
                generated_report = GeneratedReport.objects.create(**generated_report_data)
            
            self.logger.info(f"Generated report saved successfully: {generated_report.id}")
            return generated_report
            
        except Exception as e:
            self.logger.error(f"Error saving generated report: {e}")
            raise

    def get_supported_formats(self) -> list:
        """
        Devuelve una lista de formatos soportados por el generador.
        Puede ser sobreescrito por subclases.

        Returns:
            list: Lista de formatos soportados.
        """
        return [self.format_type]

    def get_default_options(self) -> Dict[str, Any]:
        """
        Devuelve un diccionario con opciones por defecto para la generación.
        Puede ser sobreescrito por subclases.

        Returns:
            Dict[str, Any]: Opciones por defecto.
        """
        return self.default_options.copy()

    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Maneja errores durante la generación y los registra.

        Args:
            error (Exception): Excepción ocurrida.
            context (str): Contexto adicional del error.

        Returns:
            Dict[str, Any]: Diccionario con información del error.
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg)
        
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }

    def cleanup_temp_files(self):
        """
        Limpia archivos temporales creados durante la generación.
        """
        for temp_path in self.temp_files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    self.logger.debug(f"Temporary file cleaned up: {temp_path}")
            except Exception as e:
                self.logger.warning(f"Could not clean up temporary file {temp_path}: {e}")
        
        # Limpiar la lista
        self.temp_files.clear()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files"""
        self.cleanup_temp_files()
