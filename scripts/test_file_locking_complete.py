#!/usr/bin/env python
"""
Test completo del sistema de file locking.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

print("="*80)
print("TEST COMPLETO - SISTEMA DE FILE LOCKING")
print("="*80)

# Test 1: Importaciones
print("\n1. Verificando importaciones...")
try:
    from apps.core.models import GeneratedFile
    from apps.core.file_locking import file_lock, FileRegistry
    from apps.core.tasks import cleanup_expired_files
    print("   ✅ Todos los módulos importados")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Modelo
print("\n2. Verificando modelo GeneratedFile...")
try:
    count = GeneratedFile.objects.count()
    print(f"   ✅ Modelo OK ({count} registros)")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: File Lock básico
print("\n3. Testeando file lock básico...")
try:
    test_file = 'data/exports/test_lock.txt'
    os.makedirs('data/exports', exist_ok=True)
    
    with file_lock(test_file, timeout=5) as lock:
        with open(test_file, 'w') as f:
            f.write("Test content")
        print("   ✅ Lock adquirido y liberado correctamente")
    
    if not os.path.exists(f"{test_file}.lock"):
        print("   ✅ Lock file eliminado correctamente")
    else:
        print("   ⚠️  Lock file no fue eliminado")
    
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: FileRegistry
print("\n4. Testeando FileRegistry...")
try:
    test_file = 'data/exports/test_registry.txt'
    with open(test_file, 'w') as f:
        f.write("Test registry content")
    
    file_record = FileRegistry.register_file(
        file_path=test_file,
        category='temp',
        ttl_hours=1,
        metadata={'test': True}
    )
    
    print(f"   ✅ Archivo registrado: ID {file_record.id}")
    print(f"      Size: {file_record.size_mb} MB")
    print(f"      MD5: {file_record.hash_md5[:10]}...")
    print(f"      Expires: {file_record.expires_at}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Exporters con locking
print("\n5. Testeando exporters con file locking...")
try:
    from apps.geodata.models import Layer
    from apps.geodata.exporters import ShapefileExporter
    
    layers = Layer.objects.filter(features__isnull=False).distinct()
    
    if layers.exists():
        layer = layers.first()
        exporter = ShapefileExporter('data/exports/test')
        
        result = exporter.export_layer(layer, filename='test_locking')
        
        print(f"   ✅ Exportación completada")
        print(f"      Archivo: {result['filename']}")
        print(f"      Tamaño: {result['size']/1024:.2f} KB")
        print(f"      File ID: {result.get('file_id', 'N/A')}")
        
        if 'file_id' in result:
            file_record = GeneratedFile.objects.get(id=result['file_id'])
            print(f"      Registrado en BD: ✅")
            print(f"      Expira: {file_record.expires_at}")
    else:
        print("   ⚠️  No hay capas con datos para testear")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Storage stats
print("\n6. Estadísticas de almacenamiento...")
try:
    stats = FileRegistry.get_storage_stats()
    for category, data in stats.items():
        print(f"   {category}: {data['count']} archivos, {data['size_mb']} MB")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("✅ TESTS COMPLETADOS")
print("="*80)
