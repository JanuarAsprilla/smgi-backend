"""
Tests for Core app.
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import os
import tempfile
from apps.core.models import GeneratedFile
from apps.core.file_locking import FileLock, FileRegistry

User = get_user_model()


class GeneratedFileModelTest(TestCase):
    """Test cases for GeneratedFile model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        # Crear archivo temporal
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        self.temp_file.write(b'Test content')
        self.temp_file.close()
        
        self.generated_file = GeneratedFile.objects.create(
            file_path=self.temp_file.name,
            category='export',
            user=self.user,
            size=12,
            expires_at=timezone.now() + timedelta(hours=24)
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
        
        lock_path = f"{self.temp_file.name}.lock"
        if os.path.exists(lock_path):
            os.remove(lock_path)
    
    def test_file_creation(self):
        """Test file is created correctly."""
        self.assertEqual(self.generated_file.category, 'export')
        self.assertEqual(self.generated_file.status, 'generating')
        self.assertEqual(self.generated_file.download_count, 0)
    
    def test_is_expired(self):
        """Test is_expired property."""
        self.assertFalse(self.generated_file.is_expired)
        
        # Cambiar fecha de expiración al pasado
        self.generated_file.expires_at = timezone.now() - timedelta(hours=1)
        self.generated_file.save()
        self.assertTrue(self.generated_file.is_expired)
    
    def test_filename_property(self):
        """Test filename property."""
        filename = self.generated_file.filename
        self.assertTrue(filename.endswith('.txt'))
    
    def test_size_mb_property(self):
        """Test size_mb property."""
        self.assertEqual(self.generated_file.size_mb, 0.0)
    
    def test_size_kb_property(self):
        """Test size_kb property."""
        self.assertEqual(self.generated_file.size_kb, 0.01)
    
    def test_exists_on_disk(self):
        """Test exists_on_disk method."""
        self.assertTrue(self.generated_file.exists_on_disk())
    
    def test_get_age_hours(self):
        """Test get_age_hours method."""
        age = self.generated_file.get_age_hours()
        self.assertGreaterEqual(age, 0)
        self.assertLess(age, 1)
    
    def test_time_until_expiry(self):
        """Test time_until_expiry method."""
        time_left = self.generated_file.time_until_expiry()
        self.assertGreater(time_left, 23)
        self.assertLess(time_left, 25)
    
    def test_mark_downloaded(self):
        """Test mark_downloaded method."""
        initial_count = self.generated_file.download_count
        
        self.generated_file.mark_downloaded()
        self.assertEqual(self.generated_file.download_count, initial_count + 1)
        self.assertIsNotNone(self.generated_file.last_accessed)
        self.assertEqual(self.generated_file.status, 'downloading')
    
    def test_mark_ready(self):
        """Test mark_ready method."""
        self.generated_file.mark_ready()
        self.assertEqual(self.generated_file.status, 'ready')
    
    def test_mark_error(self):
        """Test mark_error method."""
        self.generated_file.mark_error()
        self.assertEqual(self.generated_file.status, 'error')
    
    def test_can_be_deleted(self):
        """Test can_be_deleted method."""
        self.assertTrue(self.generated_file.can_be_deleted())
        
        # Marcar como eliminado
        self.generated_file.deleted_at = timezone.now()
        self.assertFalse(self.generated_file.can_be_deleted())
    
    def test_delete_file(self):
        """Test delete_file method."""
        self.assertTrue(os.path.exists(self.temp_file.name))
        
        self.generated_file.delete_file()
        self.assertFalse(os.path.exists(self.temp_file.name))
        self.assertIsNotNone(self.generated_file.deleted_at)
    
    def test_can_be_downloaded(self):
        """Test can_be_downloaded method."""
        # Archivo no está listo
        self.assertFalse(self.generated_file.can_be_downloaded())
        
        # Marcar como listo
        self.generated_file.mark_ready()
        self.assertTrue(self.generated_file.can_be_downloaded())
        
        # Archivo expirado
        self.generated_file.expires_at = timezone.now() - timedelta(hours=1)
        self.generated_file.save()
        self.assertFalse(self.generated_file.can_be_downloaded())
    
    def test_extend_expiration(self):
        """Test extend_expiration method."""
        original_expiry = self.generated_file.expires_at
        
        self.generated_file.extend_expiration(hours=48)
        
        self.generated_file.refresh_from_db()
        self.assertGreater(self.generated_file.expires_at, original_expiry)
    
    def test_get_download_url(self):
        """Test get_download_url method."""
        url = self.generated_file.get_download_url()
        # URL puede ser None si el archivo no está en MEDIA_ROOT
        self.assertTrue(url is None or url.startswith('/media/'))


class FileLockTest(TestCase):
    """Test cases for FileLock."""
    
    def setUp(self):
        """Set up test data."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
        
        lock_path = f"{self.temp_file.name}.lock"
        if os.path.exists(lock_path):
            os.remove(lock_path)
    
    def test_acquire_release_lock(self):
        """Test acquiring and releasing lock."""
        lock = FileLock(self.temp_file.name)
        
        self.assertTrue(lock.acquire())
        self.assertTrue(lock._locked)
        
        lock.release()
        self.assertFalse(lock._locked)
    
    def test_context_manager(self):
        """Test lock as context manager."""
        lock_path = f"{self.temp_file.name}.lock"
        
        with FileLock(self.temp_file.name) as lock:
            self.assertTrue(lock._locked)
            self.assertTrue(os.path.exists(lock_path))
        
        # Lock should be released after context
        self.assertFalse(lock._locked)
        self.assertFalse(os.path.exists(lock_path))
    
    def test_non_blocking_lock(self):
        """Test non-blocking lock acquisition."""
        lock1 = FileLock(self.temp_file.name)
        lock1.acquire()
        
        # Try to acquire again without blocking
        lock2 = FileLock(self.temp_file.name)
        result = lock2.acquire(blocking=False)
        
        self.assertFalse(result)
        
        lock1.release()


class FileRegistryTest(TestCase):
    """Test cases for FileRegistry."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        # Crear archivo temporal
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        self.temp_file.write(b'Test content for registry')
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_register_file(self):
        """Test registering a file."""
        file_record = FileRegistry.register_file(
            file_path=self.temp_file.name,
            category='export',
            user_id=self.user.id,
            ttl_hours=24
        )
        
        self.assertIsNotNone(file_record)
        self.assertEqual(file_record.category, 'export')
        self.assertEqual(file_record.user_id, self.user.id)
        self.assertGreater(file_record.size, 0)
        self.assertTrue(len(file_record.hash_md5) > 0)
    
    def test_register_file_invalid_category(self):
        """Test registering file with invalid category."""
        with self.assertRaises(ValueError):
            FileRegistry.register_file(
                file_path=self.temp_file.name,
                category='invalid_category',
                user_id=self.user.id
            )
    
    def test_register_file_duplicate(self):
        """Test registering same file twice updates existing record."""
        file_record1 = FileRegistry.register_file(
            file_path=self.temp_file.name,
            category='export',
            user_id=self.user.id
        )
        
        file_record2 = FileRegistry.register_file(
            file_path=self.temp_file.name,
            category='report',
            user_id=self.user.id
        )
        
        # Should return updated record, not create new one
        self.assertEqual(file_record1.id, file_record2.id)
        self.assertEqual(GeneratedFile.objects.filter(file_path=self.temp_file.name).count(), 1)
    
    def test_get_user_files(self):
        """Test getting user files."""
        FileRegistry.register_file(
            file_path=self.temp_file.name,
            category='export',
            user_id=self.user.id
        )
        
        files = FileRegistry.get_user_files(self.user.id)
        self.assertEqual(files.count(), 1)
        
        files_filtered = FileRegistry.get_user_files(self.user.id, category='export')
        self.assertEqual(files_filtered.count(), 1)
    
    def test_get_storage_stats(self):
        """Test getting storage statistics."""
        FileRegistry.register_file(
            file_path=self.temp_file.name,
            category='export',
            user_id=self.user.id
        )
        
        stats = FileRegistry.get_storage_stats()
        
        self.assertIn('export', stats)
        self.assertIn('total', stats)
        self.assertGreater(stats['export']['count'], 0)
        self.assertGreater(stats['total']['count'], 0)
    
    def test_cleanup_expired(self):
        """Test cleanup of expired files."""
        # Crear archivo expirado
        expired_file = GeneratedFile.objects.create(
            file_path=self.temp_file.name,
            category='temp',
            user=self.user,
            size=100,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        deleted_count, failed_count = FileRegistry.cleanup_expired()
        
        self.assertGreater(deleted_count, 0)
        
        expired_file.refresh_from_db()
        self.assertIsNotNone(expired_file.deleted_at)
